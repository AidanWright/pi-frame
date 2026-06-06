{
  description = "pi-frame: daily photo display for Waveshare 7.3\" E6 e-paper on Raspberry Pi Zero 2W";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      # Build host is x86_64; target is aarch64 (Pi Zero 2W)
      buildSystem = "x86_64-linux";
      piSystem = "aarch64-linux";

      # nixpkgs for the build host
      pkgsBuild = nixpkgs.legacyPackages.${buildSystem};

      # Cross-compilation pkgs: build on x86_64, target aarch64
      pkgsCross = nixpkgs.legacyPackages.${buildSystem}.pkgsCross.aarch64-multiplatform;

      # Pi Python package built for aarch64
      piframePkg = pkgsCross.callPackage ./pi/default.nix { pkgs = pkgsCross; };

      # Server Python package built natively
      piframeServerPkg = pkgsBuild.callPackage ./server/default.nix { pkgs = pkgsBuild; };

    in
    {
      # --- Pi SD card image ---
      nixosConfigurations.pi-frame = nixpkgs.lib.nixosSystem {
        system = piSystem;
        # Tell nixpkgs to cross-compile from x86_64
        pkgs = pkgsCross;
        specialArgs = { inherit piframePkg; };
        modules = [
          ./pi/nixos/configuration.nix
          {
            # Cross-compilation: build on x86_64
            nixpkgs.buildPlatform = buildSystem;
            nixpkgs.hostPlatform = piSystem;
          }
        ];
      };

      # Expose SD image as a top-level package for easy building
      packages.${buildSystem} = {
        pi-sd-image = self.nixosConfigurations.pi-frame.config.system.build.sdImage;
        piframe = piframePkg;
        piframe-server = piframeServerPkg;
      };

      # --- Server NixOS module (for deploying to the NixOS server) ---
      nixosModules.piframe-server = import ./server/nixos/configuration.nix;

      # --- Development shell ---
      devShells.${buildSystem}.default = pkgsBuild.mkShell {
        name = "pi-frame-dev";
        buildInputs = with pkgsBuild; [
          # Python dev
          python311
          python311Packages.pip
          python311Packages.pytest
          python311Packages.pillow
          python311Packages.flask
          python311Packages.httpx
          python311Packages.fastapi
          python311Packages.uvicorn
          python311Packages.sqlalchemy
          python311Packages.python-multipart
          # Nix tooling
          nil
          nixpkgs-fmt
          # Emulation
          qemu
          # Utilities
          jq
          curl
        ];
        shellHook = ''
          echo "pi-frame dev shell"
          echo "  Build SD image: nix build .#pi-sd-image"
          echo "  Run server:     cd server && uvicorn piframe_server.main:app --reload"
          echo "  Run pi tests:   cd pi && pytest"
          echo "  Run server tests: cd server && pytest"
          echo "  QEMU test:      bash dev/qemu-test.sh"
        '';
      };

      # Allow 'nix flake check' to validate configs
      checks.${buildSystem} = {
        pi-tests = pkgsBuild.runCommand "pi-tests" {
          buildInputs = with pkgsBuild; [
            python311
            python311Packages.pytest
            python311Packages.pillow
            python311Packages.flask
            python311Packages.httpx
            python311Packages.qrcode
          ];
        } ''
          cd ${./pi}
          python -m pytest tests/ -q
          touch $out
        '';
        server-tests = pkgsBuild.runCommand "server-tests" {
          buildInputs = with pkgsBuild; [
            python311
            python311Packages.pytest
            python311Packages.fastapi
            python311Packages.httpx
            python311Packages.sqlalchemy
            python311Packages.python-multipart
            python311Packages.pillow
            python311Packages.uvicorn
          ];
        } ''
          cd ${./server}
          python -m pytest tests/ -q
          touch $out
        '';
      };
    };
}
