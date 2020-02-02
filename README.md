# Hive

This is my work on automating my home infrastructure.

**Disclaimer**

- This repo is for me, not you. It's not directly reusable, but I hope you find it helpful.
- I've not read docs on Ansible, nor do I intend to
- First time racking anything, I'm not experienced (or an expert)

High level this project is primarily for:

- various media-related services (private)
- home assistant with a variety of configurations
- internal monitoring
- routine backups outbound to a cloud provider (gcp)

The goal is to create a memory of my home infrastructures information. Whether that means it happens via Ansible, or I simply have some record of it in git, it helps service the task of re-configuring a service if it ever needs it.

Some additional goals I have that may or may not have progress in the repo:

- local focused, especially with "smart" devices
- configured via code as much as possible, especially with home assistant
- secure and private, everythings full of exploits
- redudancy for important things in life (e.g. google photos)
- hands-free use, alert me when I need to take action

## Table of Contents

<!--ts-->
   * [Hive](#hive)
      * [Table of Contents](#table-of-contents)
      * [Architecture and Devices](#architecture-and-devices)
         * [Lights](#lights)
         * [Audio](#audio)
         * [Doors](#doors)
         * [Alarm &amp; Cameras](#alarm--cameras)
         * [Various Sensors](#various-sensors)
         * [Automations](#automations)
         * [Pi-hole](#pi-hole)
         * [NAS](#nas)
      * [Home Assistant](#home-assistant)
      * [Other](#other)
         * [Google Photos Sync](#google-photos-sync)
         * [Internal Monitoring](#internal-monitoring)
         * [VPN](#vpn)
      * [Ansible / Machine Configuration](#ansible--machine-configuration)
         * [Bootstrap](#bootstrap)
         * [Encrypted Values](#encrypted-values)
         * [Cameras](#cameras)
         * [Firewall](#firewall)
   * [References](#references)

<!-- Added by: dcramer, at: Fri Jan 31 23:29:30 PST 2020 -->

<!--te-->

## Architecture and Devices

There's a variety of things going on, so here's the ongoing list of projects. You'll find some opinions on what sucks, and what doesn't. One important thing to note, my goal was to be decoupled from a specific vendor (e.g. no Nest) and use products with APIs, though that hasn't nessesarily worked or made things better.

I'm using a pretty status-quo rack mounted Unifi network architecture. I've got a gen2 controller to support Unifi Protect (Ubiquiti's newest iteration of its NVR), as well as a USG and PoE switch.

Everything's managed in a mid-depth rack in my garage, which aims to rack mount anything it possible can. The rack itself is a 42U design from Navepoint, 800mm deep.

[![Rack](/img/rack-th.jpg)](/img/rack.jpg)

(Yes, I realize theres fingerprints on it)

The rack consists of the following devices:

- 4x Sonos AMPs
- 24 bay Supermicro NAS (thanks serverstore.com!)
- GPU-less overkill server (straight forward desktop PC in a rack case)
- Pi-hole (experimental still)
- Hue hub (legacy)
- SimpliSafe hub (not lovin it)
- Lutron Connect bridge
- Unifi USG
- Unifi 24 port PoE switch
- Unifi Gen2 pro controller
- Unifi AP (temporary, will be mounted elsewhere soon)

There are 5 PoE cameras running to the switch, all external to the living space.

I'm quite happy with what I've pulled off here given I've never done this before. It looks clean, operates fairly quiet, and has future expansion space.

### Lights

Nearly all lights are from a Lutron (Radio RA2) system, using the standard telnet APIs. They're mostly configured here to make them accessible to Google Home via Home Assistant (via Nabu Casa's cloud service).

I've got a few hue bulbs as well that are collecting dust.

Other than Lutron's telnet API randomly not working for a while, I'm generally happy with the system.

### Audio

I've got a cluster of Sonos amps powering some built-in speakers in various rooms. There's not a lot going on here other than them existing, being rack mounted, and used for some automations. I'd love for Sonos to have more open APIs, but otherwise it's exactly what you pay for.

### Doors

WIP. I'm planning to install an Axis door station so I can go keyfob at home (ya ya, I dont want to hear about it). I've got one Yale lock I installed to test, but to be honest it's not to the level of polish or maturity I would have expected these devices be. It's probably one of the best in its class, I just think they're all bad. I'm opting for prosumer or commercial grade where I can and trying to make more thoughtful decisions on everything else. Thus the reason I'm looking at Axis.

### Alarm & Cameras

I have a SimpliSafe alarm system that seemed like a great idea at the time, and then I realizd all of the local APIs are encrypted and recently it stopped working with HASS. Turns out all of the security systems are tightly locked to vendors (not literally all, but any that dont look like shit). I'll suck it up with this since it's only the core alarms and sensors.

Additionally I have various Ubiquiti security cameras which archive footage to the NAS.

### Various Sensors

There are a variety of Aeotec sensors that I've setup to get a feel for what might be possible. I've had mixed results and wouldn't go as far as recommending them (though I'm new to this).

Additionally, and probably the thing that's worked the best, I'm using Sonoff smart plugs (w/ tasmoto firmware) for power monitoring high value devices, which let's me drive some interesting automations. For example, when the dryer finishes I've got it setup to broadcast via Sonos a simple text-to-speech notification.

### Automations

My favorite choice so far has been opting for a Telegram bot to drive the system. I really wanted to make things be reactive - that is, I have no desire to watch or visit a dashboard (sorry my home assistant UI is bland). The Telegram bot is intended ot notify me of important activities, often a substitute for an email, but also allow me to react ot them. For example, if the garage has been left open for a period of time, let me know, and give me a quick action to close the garage. I also intend to bundle camera feeds or snapshots to these important events.

This is still very much a work in progress, and I'm hoping to contribute back to Home Assitant to make it easier to do more powerful automations primarily via the alerts subsystem.

### Pi-hole

I followed [this guide](https://learn.adafruit.com/pi-hole-ad-pitft-tft-detection-display) to setup the raspberry pi with pi-hole. It does the job, but I worry about its lack of redudancy given its acting as the single DNS server. I'm still treating this as an experiment, as I dont really have a desire to block ads at the network level (not all ads are bad, yo), but it was a fun quick build.

### NAS

The NAS is running Unraid (great UI!), and has been doing well. I picked up the server itself off of theserverstore.com (rec from a friend) and am super happy with it. Its a refurbished 24 bay 4U dual xeon, 60 gigs of memory that sit there and collect dust. I was previously using a Synology 8 bay, but I stupidly chose Raid 10 and couldn't expand the raid without a bigger set of drive bays (can't add drives, how is that not possible with Raid10). Figured this was a (far) better spend of dollars than a larger Synology. That said, Synology's been great, it's just too expensive.

## Home Assistant

A bulk of my time has been spent playing with Home Assistant. I'm not really into much of the smart home endeavor, but I enjoy building things. Many of the configurations are unfinished, and may not be working at all, but I've been spending a lot of time on maintainable structure.

I have had a few goals in mind when playing with it:

- focus on alerts and non-hass interactions (voice, telegram bot)
- as much as possible, the configuration is in this repo (wish could be even more so)
- remove cruft that turns out not to be valuable

You'll find the bulk of this in the ``hive.hass`` role, which I'm told is not terribly done. I also have some overkill early work at re-architecting home assistant alerts on top of appdaemon to make my (builders) life easier.

What I'm enjoying so far:

- the washer/dryer alerts are literally the GREATEST THING EVER
- the telegram bot is awesome, though its only as good as the automations
- google cloud integration (using Nabu Casa / hass cloud) has worked extremely well, and was easy to configure
- some custom widgets for garbage collection and train/bus times

What has failed miserably:

- simplisafe: recently it just stopped working (probably related to their new 2fa push)
- ecobee: probably gonna get replaced
- mopar: i just wanted to telegram myself when I've left my car doors unlocked at home
- aeotec: one of the sensors barely ever works, the others have been _fine_

## Other

### Google Photos Sync

I'm using [gphotos-sync](https://pypi.org/project/gphotos-sync/) -- which is clearly someones ocean of sweat and tears -- to automatically pull down copies of my photos. I'm not worried about Google ditching this product, so its more of an exercise to achieve it. It doesn't work perfectly (see the project for limitations), but hopefully Google will improve this over time.

You'll find the automation for this in ``hive.gphotos``.

### Internal Monitoring

There's a weak Kibana and Influx setup. It's not highly functional, and I'm not really sure what I was thinking when I thought it was a good idea.

There's a cool generic dashboard with an endless list of system metrics though.

### VPN

I previously was running an Intel Nuc with a bunch of services and had that configured to route all traffic through Private Internet Access. I haven't gotten around to making it work well, and may not ever do it. There's remnants of that in the README as well as some efforts in the ``hive.pia`` role.

## Ansible / Machine Configuration

This is mostly scattered notes so I remember how anything works in disaster scenarios.

### Bootstrap

```shell
sudo apt-add-repository -y ppa:ansible/ansible
sudo apt-get update
sudo apt-get install -y ansible
```

### Encrypted Values

Hopefully everything personally identifiable is encrypted, as well as the various external accounts. I'm sure ya'll can Google my address and phone number, but it seemed like a straight forward approach to anonymizing much of the information.

It needs `ansible-passwd` defined w/ the vault password (which I store in 1Password).

Strings are then encrypted bit-by-bit, which frankly is a pain in the ass:

```
ansible-vault encrypt-string [value]
```

### Cameras

Cameras are all Unifi protect devices from Ubiquiti. To configure them for hass do the following:

- Hit IP directly
- Login with ubnt + password (found in protect settings)
- Enable anonymous snapshot

In protect itself:

- Hit Cameras
- Enable [Medium] RSTP stream

The ``hive.protect`` role will attempt to auto archive footage automatically to the nas.

### Firewall

TODO: I've yet to re-implement this, and may take another pass.

The goal here is to route all external traffic through a VPN provider to create an additional layer of privacy.

Configure IP tables via `ufw`:

```
sudo apt-get install ufw
```

This denies all in and outgoing traffic:

```
sudo ufw default deny outgoing
sudo ufw default deny incoming
```

Optional step for OpenSSH users or if you want to allow/block a specific service:

```
sudo ufw app list //will show some services, OpenSSH among others
sudo ufw OpenSSH allow //allows OpenSHH. this works for other services too
```

Allow traffic to VPN interface:

```
# replace "tun0" with your vpn interface name --> see sudo ifconfig
sudo ufw allow out on tun0 from any to any
# replace "tun0" with your vpn interface name --> see sudo ifconfig
sudo ufw allow in on tun0 from any to any
```

Allow OpenVPN connections to PIA:

```
sudo ufw allow out vpn
```

This allows all traffic from and to the VPN server (US Silicon Valley):

```
sudo ufw allow in from 104.156.228.0/104.156.228.255 to any
sudo ufw allow out from any to 104.156.228.0/104.156.228.255
```

This step allows connections within your LAN:

```
sudo ufw allow in from 10.0.0.0/8
sudo ufw allow out to 10.0.0.0/8
sudo ufw allow in from 172.16.0.0/12
sudo ufw allow out to 172.16.0.0/12
sudo ufw allow in from 192.168.0.0/16
sudo ufw allow out to 192.168.0.0/16
sudo ufw allow in from fd00::/8
sudo ufw allow out to fd00::/8
```

Allow various network services:

```
sudo ufw allow out bonjour
sudo ufw allow out samba
```

```
sudo ufw allow proto udp from 192.168.0.0/16 to any port 137
sudo ufw allow proto udp from 192.168.1.0/24 to any port 138
sudo ufw allow proto tcp from 192.168.1.0/24 to any port 139
sudo ufw allow proto tcp from 192.168.1.0/24 to any port 445
```

Allow all requests to HTTPS services:

```
sudo ufw allow out proto tcp from any to any port 443
```

Enable the firewall:

```
sudo ufw enable
```

# References

- https://tasmota.github.io/docs/#/integrations/Home-Assistant
