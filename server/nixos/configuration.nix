{ config, pkgs, lib, piframeServerPkg ? null, ... }:

# Optional NixOS module for the pi-frame backend server.
# Import into your server's configuration.nix:
#
#   imports = [ /path/to/pi-frame/server/nixos/configuration.nix ];
#
# Required environment variables (set via EnvironmentFile or secrets manager):
#   PIFRAME_API_KEY       - API key for authenticating uploads
#   TAILSCALE_TAILNET     - Tailscale tailnet name (for server→Pi push)
#   STORAGE_PATH          - Directory for image storage (default: /var/lib/piframe-server/images)

{
  options.services.piframe-server = with lib; {
    enable = mkEnableOption "pi-frame backend server";
    port = mkOption {
      type = types.port;
      default = 8000;
      description = "Port to listen on";
    };
    environmentFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "Path to a file containing PIFRAME_API_KEY and TAILSCALE_TAILNET";
    };
    storagePath = mkOption {
      type = types.str;
      default = "/var/lib/piframe-server/images";
      description = "Directory where uploaded images are stored";
    };
  };

  config = lib.mkIf config.services.piframe-server.enable {
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
          "${pkgs.python3}/bin/uvicorn"
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
  };
}
