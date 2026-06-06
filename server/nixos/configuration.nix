{ config, pkgs, lib, ... }:

{
  options.services.piframe-server = with lib; {
    enable = mkEnableOption "pi-frame backend server";
    port = mkOption {
      type = types.port;
      default = 8000;
    };
    environmentFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "File containing PIFRAME_API_KEY, PIFRAME_ADMIN_PASSWORD, PIFRAME_USER_PASSWORD, and optionally TAILSCALE_TAILNET";
    };
    storagePath = mkOption {
      type = types.str;
      default = "/var/lib/piframe-server/images";
    };
  };

  config = lib.mkIf config.services.piframe-server.enable (
    let
      pkg = pkgs.callPackage ../default.nix { inherit pkgs; };
    in {
      systemd.services.piframe-server = {
        description = "pi-frame backend server";
        after = [ "network.target" ];
        wantedBy = [ "multi-user.target" ];

        environment = {
          STORAGE_PATH = config.services.piframe-server.storagePath;
          DATABASE_URL = "sqlite:////var/lib/piframe-server/piframe.db";
        };

        serviceConfig = {
          Type = "simple";
          User = "piframe-server";
          Group = "piframe-server";
          ExecStart = lib.concatStringsSep " " [
            "${pkg}/bin/uvicorn"
            "piframe_server.main:app"
            "--host" "0.0.0.0"
            "--port" (toString config.services.piframe-server.port)
          ];
          EnvironmentFile = lib.mkIf (config.services.piframe-server.environmentFile != null)
            config.services.piframe-server.environmentFile;
          Restart = "on-failure";
          RestartSec = "5s";
          StateDirectory = "piframe-server";
        };
      };

      users.users.piframe-server = {
        isSystemUser = true;
        group = "piframe-server";
        home = "/var/lib/piframe-server";
        createHome = true;
      };
      users.groups.piframe-server = { };

      systemd.tmpfiles.rules = [
        "d ${config.services.piframe-server.storagePath} 0755 piframe-server piframe-server -"
      ];
    }
  );
}
