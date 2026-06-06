{ config, pkgs, lib, piframePkg, modulesPath, ... }:

# piframePkg is passed via flake specialArgs (the built Python package)

{
  imports = [
    "${modulesPath}/installer/sd-card/sd-image-aarch64.nix"
    ./hardware.nix
    ./wifi.nix
    ./tailscale.nix
    ./piframe-service.nix
    ./image.nix
  ];

  system.stateVersion = "24.11";

  time.timeZone = "UTC";
  i18n.defaultLocale = "en_US.UTF-8";

  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = true;
      PermitRootLogin = "no";
    };
  };

  users.users.frame = {
    isNormalUser = true;
    # initialPassword is stored in the Nix store — fine for a home device,
    # change it after first boot if the Pi is ever internet-accessible.
    initialPassword = "frame";
    extraGroups = [ "wheel" ];
  };

  security.sudo.wheelNeedsPassword = false;

  # Minimal package set
  environment.systemPackages = with pkgs; [
    vim
    htop
    jq
    curl
    piframePkg
  ];

  networking.hostName = "pi-frame";
}
