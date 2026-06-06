{ pkgs, lib, ... }:

{
  # RPi Foundation kernel tuned for BCM2837 (same silicon as Pi 3)
  boot.kernelPackages = pkgs.linuxPackages_rpi02w;

  # Maximize usable RAM: minimal GPU allocation, ZRAM swap
  sdImage.extraFirmwareConfig = {
    gpu_mem = 16;
  };
  zramSwap = {
    enable = true;
    algorithm = "zstd";
  };

  # Serial console on ttyAMA0 (3-pin debug header on the PhotoPainter HAT)
  boot.kernelParams = [
    "console=ttyAMA0,115200"
    "console=tty1"
    "8250.nr_uarts=1"
  ];
  systemd.services."serial-getty@ttyAMA0" = {
    enable = true;
    wantedBy = [ "getty.target" ];
  };

  # SPI0 for the e-paper display (CE0 = GPIO8)
  # Equivalent to dtparam=spi=on in config.txt
  hardware.deviceTree.overlays = [
    {
      name = "spi0-1cs-overlay";
      dtsText = ''
        /dts-v1/;
        /plugin/;
        / {
          compatible = "brcm,bcm2835";
          fragment@0 {
            target = <&spi0>;
            __overlay__ {
              status = "okay";
              cs-gpios = <&gpio 8 1>;
              #address-cells = <1>;
              #size-cells = <0>;
              spidev@0 {
                compatible = "spidev";
                reg = <0>;
                #address-cells = <1>;
                #size-cells = <0>;
                spi-max-frequency = <4000000>;
              };
            };
          };
          fragment@1 {
            target = <&gpio>;
            __overlay__ {
              spi0_cs_pins: spi0_cs_pins {
                brcm,pins = <8>;
                brcm,function = <1>;
              };
            };
          };
        };
      '';
    }

    # I2C1 for DS3231 (RTC, 0x68) and INA219 (battery monitor, 0x40)
    {
      name = "i2c1-enable-overlay";
      dtsText = ''
        /dts-v1/;
        /plugin/;
        / {
          compatible = "brcm,bcm2835";
          fragment@0 {
            target = <&i2c1>;
            __overlay__ {
              status = "okay";
              clock-frequency = <100000>;
            };
          };
        };
      '';
    }

    # DS3231 RTC at I2C address 0x68
    {
      name = "i2c-rtc-ds3231-overlay";
      dtsText = ''
        /dts-v1/;
        /plugin/;
        / {
          compatible = "brcm,bcm2835";
          fragment@0 {
            target = <&i2c1>;
            __overlay__ {
              #address-cells = <1>;
              #size-cells = <0>;
              ds3231: ds3231@68 {
                compatible = "maxim,ds3231";
                reg = <0x68>;
                status = "okay";
              };
            };
          };
        };
      '';
    }
  ];

  # udev rules: give piframe user access to SPI/I2C/GPIO devices
  # Also sync system clock from DS3231 RTC when the rtc0 device appears
  services.udev.extraRules = ''
    SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"
    SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0660"
    KERNEL=="gpiomem", GROUP="gpio", MODE="0660"
    KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"
    KERNEL=="rtc0", RUN+="${pkgs.util-linux}/bin/hwclock --hctosys --utc"
  '';

  users.groups.spi = { };
  users.groups.i2c = { };
  users.groups.gpio = { };

  # NTP for when online (RTC fills the gap when offline)
  services.timesyncd.enable = true;
}
