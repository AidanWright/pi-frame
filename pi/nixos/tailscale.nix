{ pkgs, ... }:

{
  services.tailscale.enable = true;

  # Pre-auth key written by the boot-partition activation script
  services.tailscale.authKeyFile = "/etc/piframe/tailscale-authkey";

  # Idempotent one-shot service: authenticate to Tailscale after WiFi is up
  systemd.services.tailscale-autoconnect = {
    description = "Tailscale initial authentication";
    after = [ "tailscaled.service" "piframe-wifi.service" "network-online.target" ];
    wants = [ "tailscaled.service" "network-online.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      # Only call tailscale up if not already authenticated
      if ! ${pkgs.tailscale}/bin/tailscale status --json 2>/dev/null | ${pkgs.gnugrep}/bin/grep -q '"Online":true'; then
        KEY_FILE=/etc/piframe/tailscale-authkey
        if [ -f "$KEY_FILE" ]; then
          ${pkgs.tailscale}/bin/tailscale up \
            --authkey="$(cat "$KEY_FILE")" \
            --hostname=pi-frame \
            --accept-routes
        else
          echo "No Tailscale auth key found at $KEY_FILE; skipping"
        fi
      fi
    '';
  };

  # Allow Tailscale UDP port
  networking.firewall.allowedUDPPorts = [ 41641 ];
}
