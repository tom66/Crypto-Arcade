# reset display
stty -F /dev/ttyS0 115200
sleep 0.1
echo "\x1B\x40" > /dev/ttyS0
sleep 0.1
echo "\x0C" > /dev/ttyS0
sleep 0.1