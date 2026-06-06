{ pkgs, lib, ... }:

{
  sdImage = {
    imageName = "pi-frame.img";
    compressImage = false;
  };

  # On first boot, read secrets from the FAT boot partition and write them to /etc/piframe/
  # The user copies piframe-config.json to the SD card's boot partition before inserting it.
  system.activationScripts.piframe-secrets = {
    text = ''
      BOOT_CFG="/boot/piframe-config.json"
      DONE="/boot/piframe-config.done"
      SECRET_DIR="/etc/piframe"

      if [ -f "$BOOT_CFG" ] && [ ! -f "$DONE" ]; then
        echo "pi-frame: reading secrets from $BOOT_CFG"
        mkdir -p "$SECRET_DIR"
        chmod 700 "$SECRET_DIR"

        ${pkgs.jq}/bin/jq -r '.server_url // ""'        "$BOOT_CFG" > "$SECRET_DIR/server-url"
        ${pkgs.jq}/bin/jq -r '.api_key // ""'           "$BOOT_CFG" > "$SECRET_DIR/api-key"
        ${pkgs.jq}/bin/jq -r '.tailscale_authkey // ""' "$BOOT_CFG" > "$SECRET_DIR/tailscale-authkey"

        chmod 600 "$SECRET_DIR"/*
        mv "$BOOT_CFG" "$DONE"
        echo "pi-frame: secrets written; boot config renamed to $DONE"
      fi
    '';
    deps = [ ];
  };

  # Ensure /etc/piframe exists even without the secrets file
  systemd.tmpfiles.rules = [
    "d /etc/piframe 0700 root root -"
  ];
}
