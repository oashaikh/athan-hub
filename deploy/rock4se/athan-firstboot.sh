#!/usr/bin/env bash
# One-shot first-boot setup for the fresh Athan image: key-only admin login, no trim.
set -u
exec >>/var/log/athan-firstboot.log 2>&1
echo "$(date -Is) first boot setup"
timedatectl set-timezone Europe/London || true
hostnamectl set-hostname athan || true
systemctl mask fstrim.timer fstrim.service e2scrub_all.timer || true
id athan >/dev/null 2>&1 || useradd --create-home --shell /bin/bash --user-group --groups sudo,audio,video,plugdev,bluetooth athan
passwd --lock athan || true
install -d -o athan -g athan -m 0700 /home/athan/.ssh
install -o athan -g athan -m 0600 /usr/local/share/athan/authorized_keys /home/athan/.ssh/authorized_keys
install -o root -g root -m 0440 /usr/local/share/athan/90-athan-sudoers /etc/sudoers.d/90-athan
install -o root -g root -m 0644 /usr/local/share/athan/99-athan-ssh.conf /etc/ssh/sshd_config.d/99-athan.conf
for u in radxa rock; do id $u >/dev/null 2>&1 && passwd --lock $u; done
systemctl enable ssh.service; systemctl restart ssh.service
systemctl disable athan-firstboot.service
echo "$(date -Is) first boot setup done"
