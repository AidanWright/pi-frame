{
  description = "pi-frame: daily photo display for Waveshare 7.3\" E6 e-paper on Raspberry Pi Zero 2W";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nixos-hardware.url = "github:NixOS/nixos-hardware";
  };

  outputs = { self, nixpkgs, flake-utils, nixos-hardware }:
    let
      # SD image cross-compilation must run on x86_64-linux (needs Linux binfmt)
      sdBuildSystem = "x86_64-linux";
      piSystem = "aarch64-linux";

      # piframePkg (aarch64-linux) is always cross-compiled from x86_64-linux
      pkgsSdBuild = nixpkgs.legacyPackages.${sdBuildSystem};
      pkgsCross = pkgsSdBuild.pkgsCross.aarch64-multiplatform;
      piframePkg = pkgsCross.callPackage ./pi/default.nix { pkgs = pkgsCross; };

    in
    # Per-system outputs: devShell, server package, and tests work on any developer machine
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        piframeServerPkg = pkgs.callPackage ./server/default.nix { pkgs = pkgs; };
      in
      {
        # --- Development shell ---
        devShells.default = pkgs.mkShell {
          name = "pi-frame-dev";
          buildInputs = with pkgs; [
            # Python with all dev/test dependencies in one environment
            (python312.withPackages (ps: with ps; [
              pytest
              pillow
              flask
              httpx
              fastapi
              uvicorn
              sqlalchemy
              python-multipart
              qrcode
            ]))
            # Nix tooling
            nil
            nixpkgs-fmt
            # Utilities
            jq
            curl
          ] ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
            # Linux-only: QEMU for Pi emulation
            qemu
          ];
          shellHook = ''
            echo "pi-frame dev shell"
            echo "  Build SD image: nix build .#pi-sd-image  (requires x86_64-linux)"
            echo "  Run server:     cd server && uvicorn piframe_server.main:app --reload"
            echo "  Run pi tests:   cd pi && pytest"
            echo "  Run server tests: cd server && pytest"
            echo "  QEMU test:      bash dev/qemu-test.sh  (Linux only)"
          '';
        };

        # --- Packages ---
        packages = {
          piframe-server = piframeServerPkg;
        } // pkgs.lib.optionalAttrs (system == sdBuildSystem) {
          # SD image and Pi package can only be built on x86_64-linux
          pi-sd-image = self.nixosConfigurations.pi-frame.config.system.build.sdImage;
          piframe = piframePkg;
        };

        # --- CI checks ---
        checks = {
          pi-tests = pkgs.runCommand "pi-tests" {
            buildInputs = with pkgs; [
              python312
              python312Packages.pytest
              python312Packages.pillow
              python312Packages.flask
              python312Packages.httpx
              python312Packages.qrcode
            ];
            PYTHONPATH = "${./pi}/src";
          } ''
            cd ${./pi}
            python -m pytest tests/ -q
            touch $out
          '';
          server-tests = pkgs.runCommand "server-tests" {
            buildInputs = with pkgs; [
              python312
              python312Packages.pytest
              python312Packages.fastapi
              python312Packages.httpx
              python312Packages.sqlalchemy
              python312Packages.python-multipart
              python312Packages.pillow
              python312Packages.uvicorn
            ];
            PYTHONPATH = "${./server}/src";
          } ''
            cd ${./server}
            python -m pytest tests/ -q
            touch $out
          '';
        };
      }
    ) // {
      # --- Pi SD card image (cross-compiled on x86_64-linux) ---
      nixosConfigurations.pi-frame = nixpkgs.lib.nixosSystem {
        specialArgs = { inherit piframePkg; };
        modules = [
          nixos-hardware.nixosModules.raspberry-pi-3
          ./pi/nixos/configuration.nix
          {
            nixpkgs.buildPlatform = sdBuildSystem;
            nixpkgs.hostPlatform = piSystem;
          }
        ];
      };

      # --- Server NixOS module (for deploying to the NixOS server) ---
      nixosModules.piframe-server = import ./server/nixos/configuration.nix;
    };
}
