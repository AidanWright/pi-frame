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
            cachix
            # Utilities
            jq
            curl
            qemu
          ];
          shellHook = ''
            export PYTHONPATH="$PWD/server/src:$PWD/pi/src''${PYTHONPATH:+:$PYTHONPATH}"
            export DATABASE_URL="''${DATABASE_URL:-sqlite:///$PWD/dev/data/piframe.db}"
            export STORAGE_PATH="''${STORAGE_PATH:-$PWD/dev/data/images}"
            export PIFRAME_API_KEY="''${PIFRAME_API_KEY:-dev-key}"
            export PIFRAME_ADMIN_PASSWORD="''${PIFRAME_ADMIN_PASSWORD:-dev-admin}"
            export PIFRAME_USER_PASSWORD="''${PIFRAME_USER_PASSWORD:-dev-user}"
            echo "pi-frame dev shell"
            echo "  Build SD image:   nix build .#pi-sd-image  (requires x86_64-linux)"
            echo "  Run server:       uvicorn piframe_server.main:app --reload"
            echo "  Run pi tests:     cd pi && pytest"
            echo "  Run server tests: cd server && pytest"
            echo "  QEMU test:        bash dev/qemu-test.sh  (Linux only)"
          '';
        };

        # --- Packages ---
        packages = {
          piframe-server = piframeServerPkg;
        } // pkgs.lib.optionalAttrs (system == sdBuildSystem) {
          # SD image, Pi package, and server VM can only be built on x86_64-linux
          pi-sd-image = self.nixosConfigurations.pi-frame.config.system.build.sdImage;
          piframe = piframePkg;
          piframe-server-vm = self.nixosConfigurations.piframe-server-vm.config.system.build.vm;
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
            export DATABASE_URL="sqlite:///$TMPDIR/test.db"
            export STORAGE_PATH="$TMPDIR/images"
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

      # --- Server VM for local testing ---
      nixosConfigurations.piframe-server-vm = nixpkgs.lib.nixosSystem {
        system = sdBuildSystem;
        modules = [
          "${nixpkgs}/nixos/modules/virtualisation/qemu-vm.nix"
          self.nixosModules.piframe-server
          ./dev/vm-server.nix
        ];
      };
    };
}
