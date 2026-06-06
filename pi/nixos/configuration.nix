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

  # SSH for debugging (key-only auth)
  services.openssh = {
    enable = true;
    settings = {
      PasswordAuthentication = false;
      PermitRootLogin = "prohibit-password";
    };
  };

  # Minimal package set
  environment.systemPackages = with pkgs; [
    vim
    htop
    git
    jq
    curl
    piframePkg
  ];

  networking.hostName = "pi-frame";
}
