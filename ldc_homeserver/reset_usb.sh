#!/bin/bash
usb="0483:5740" # Find ME, Replace the ID 

cam=$(lsusb | awk "/$usb/ {print $6}")
echo $cam
if [ ! -z "$cam" -a "$cam" != " " ]; then
  for X in /sys/bus/usb/devices/*;
  do
    a=$(cat "$X/idVendor" 2>/dev/null)
    b=$(cat "$X/idProduct" 2>/dev/null)
    c="$a:$b"
    # if [ ! -z "$c" -a "$c" != " " ] && [ "$c" == "$usb" ]; then
    if ! -z "$c" -a "$c" != " "  && "$c" == "$usb"; then
      d=$(echo $X | sed "s/\/sys\/bus\/usb\/devices\///g")
      echo "[FOUND] $d"

      # sudo sh -c "echo 0 > /sys/bus/usb/devices/$d/authorized"
      sleep 2
      # sudo sh -c "echo 1 > /sys/bus/usb/devices/$d/authorized"
      lsusb
      break

    fi
  done;
fi