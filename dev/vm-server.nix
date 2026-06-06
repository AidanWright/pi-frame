{ ... }:
{
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  services.piframe-server.enable = true;

  # Test credentials baked in — not for production use
  systemd.services.piframe-server.environment = {
    PIFRAME_API_KEY = "dev-key";
    PIFRAME_ADMIN_PASSWORD = "dev-admin";
    PIFRAME_USER_PASSWORD = "dev-user";
  };

  virtualisation = {
    forwardPorts = [
      { from = "host"; host.port = 8000; guest.port = 8000; }
    ];
    graphics = false;
    memorySize = 1024;
  };

  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = "yes";
      PasswordAuthentication = true;
    };
  };
  users.users.root.password = "root";

  system.stateVersion = "24.11";
}
