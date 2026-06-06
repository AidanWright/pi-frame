{ config, pkgs, lib, piframePkg, ... }:

{
  # Main display refresh service (run by daily timer and on-demand by push listener)
  systemd.services.piframe = {
    description = "pi-frame display refresh";
    after = [ "piframe-wifi.service" "tailscale-autoconnect.service" "network-online.target" ];
    wants = [ "piframe-wifi.service" "network-online.target" ];
    serviceConfig = {
      Type = "oneshot";
      User = "piframe";
      Group = "piframe";
      ExecStart = "${piframePkg}/bin/piframe-main";
      StandardOutput = "journal";
      StandardError = "journal";
      # Allow access to hardware devices
      SupplementaryGroups = "spi i2c gpio";
    };
  };

  # Daily timer: trigger display refresh every morning
  systemd.timers.piframe = {
    description = "pi-frame daily display update";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 08:00:00";
      Persistent = true;  # catch up if the Pi was sleeping
    };
  };

  # Push listener service: always-on Flask endpoint on Tailscale interface
  systemd.services.piframe-listener = {
    description = "pi-frame push listener";
    after = [ "tailscale-autoconnect.service" "piframe-wifi.service" ];
    wants = [ "tailscale-autoconnect.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "simple";
      User = "piframe";
      Group = "piframe";
      ExecStart = "${piframePkg}/bin/piframe-listener";
      Restart = "on-failure";
      RestartSec = "5s";
      StandardOutput = "journal";
      StandardError = "journal";
      SupplementaryGroups = "spi i2c gpio";
    };
  };

  # piframe system user
  users.users.piframe = {
    isSystemUser = true;
    group = "piframe";
    home = "/var/lib/piframe";
    createHome = true;
    extraGroups = [ "spi" "i2c" "gpio" ];
  };
  users.groups.piframe = { };
}
