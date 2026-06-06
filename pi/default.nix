{ pkgs }:

pkgs.python3Packages.buildPythonApplication {
  pname = "piframe";
  version = "0.1.0";

  src = ./.;
  pyproject = true;

  build-system = [ pkgs.python3Packages.hatchling ];

  propagatedBuildInputs = with pkgs.python3Packages; [
    pillow
    flask
    httpx
    qrcode
  ];

  # spidev, gpiozero, smbus2 are not in nixpkgs — they are hardware-specific
  # and only available on the Pi at runtime.  We skip them here.
  doCheck = false;
}
