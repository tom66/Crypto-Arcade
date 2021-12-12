# reset display
stty -F /dev/ttyS0 115200
sleep 0.1
echo -n -e "\x1B\x40" > /dev/ttyS0
sleep 0.1
echo -n -e "\x0C" > /dev/ttyS0
sleep 0.1