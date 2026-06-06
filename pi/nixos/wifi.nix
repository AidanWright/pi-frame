{ pkgs, ... }:

# Custom WiFi management: scan → try known networks → AP captive portal fallback.
# We do NOT use networking.wireless (NixOS module) because its declarative config
# conflicts with our dynamic credential management.
{
  # Disable the NixOS wireless module to avoid conflicts
  networking.wireless.enable = false;
  networking.useDHCP = false;

  # All networking on wlan0 is managed by piframe-wifi.service
  networking.interfaces.wlan0 = { };

  # Packages needed by the wifi manager script
  environment.systemPackages = with pkgs; [
    wpa_supplicant
    hostapd
    dnsmasq
    iw
    dhcpcd
    iproute2
    wirelesstools
  ];

  # Allow captive portal and push listener ports through the firewall
  networking.firewall.allowedTCPPorts = [ 80 8080 ];

  # The piframe-wifi service runs the Python wifi manager (scan→connect→AP fallback)
  systemd.services.piframe-wifi = {
    description = "pi-frame WiFi manager";
    wantedBy = [ "multi-user.target" ];
    before = [ "network-online.target" "piframe.service" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.python3}/bin/piframe-wifi-manager";
      Restart = "on-failure";
      StandardOutput = "journal";
      StandardError = "journal";
    };
  };

  # Ensure /var/lib/piframe exists and is writable by the piframe user
  systemd.tmpfiles.rules = [
    "d /var/lib/piframe 0755 piframe piframe -"
  ];
}
