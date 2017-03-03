# Network configuration

## Ref

https://minibianpi.wordpress.com/how-to/rpi3/
https://minibianpi.wordpress.com/how-to/wifi/

```bash
apt-get update
apt-get install firmware-brcm80211 wpasupplicant

vi /etc/network/interfaces
#allow-hotplug wlan0
#iface wlan0 inet manual
#wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf
#iface default inet dhcp

vi /etc/wpa_supplicant/wpa_supplicant.conf
# network={
#     ssid="NoInternetAccess"
#     psk="unaclave"
# }

apt-get install iw crda wireless-regdb
apt-get install wireless-tools

reboot
```

## Dev packages

```bash
apt-get install git vim

# Python 3.6
wget https://www.python.org/ftp/python/3.6.0/Python-3.6.0.tgz
tar xvf Python-3.6.0.tgz
cd Python-3.6.0
./configure --enable-optimizations
make -j8
sudo make altinstall
python3.6 --version
```

## Virtual env setup

```bash
python3.6 -m venv .env

source .env/bin/activate
pip install -r requirements.txt
```
