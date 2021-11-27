import pygame, sys, pprint, copy, time, struct

pygame.init()

DEMO_SCALE = 8
VFD_WIDTH = 112
VFD_HEIGHT = 16
DAMAGE_ROWS = 2
DAMAGE_ROW_HEIGHT = 8

COL_WHITE = (255, 255, 255)
COL_BLACK = (0, 0, 0)

ENABLE_DAMAGE_DEBUG = True

try:
    import RPi.GPIO as GPIO
    import serial
    AM_A_PI = True
except ImportError:
    GPIO = None
    AM_A_PI = False

def clamp(val, minval, maxval):
    if val < minval: return minval
    if val > maxval: return maxval
    return val

class VFD(object):
    window = None
    vfd_surf = None
    last_vfd_surf = None
    frame = 0
    damage_rows = []
    
    def __init__(self, render_window):
        if render_window:
            self.window = pygame.display.set_mode(size=(VFD_WIDTH * DEMO_SCALE, VFD_HEIGHT * DEMO_SCALE))
        else:
            self.window = None
            
        self.vfd_surf = pygame.Surface(size=(VFD_WIDTH, VFD_HEIGHT))
        self.vfd_surf.fill((0, 0, 0))
            
        self.temp_surf = pygame.Surface(size=(VFD_WIDTH, VFD_HEIGHT))
        self.temp_surf.fill((0, 0, 0))
        
        self.damage_surf = pygame.Surface(size=(VFD_WIDTH, VFD_HEIGHT), flags=pygame.SRCALPHA)
        self.damage_surf.fill((0, 0, 0, 0))
        
        self.last_vfd_surf = pygame.Surface(size=(VFD_WIDTH, VFD_HEIGHT))
        self.last_vfd_surf.fill((0, 0, 0))
        
        self.inv_surf = pygame.Surface(size=(VFD_WIDTH, VFD_HEIGHT))
        self.inv_surf.fill((255, 255, 255))

        if AM_A_PI:
            print("I'm running on a Pi.  I have GPIO control.")
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(23, GPIO.IN)
            self.port = serial.Serial(port="/dev/ttyS0", baudrate=115200)
        else:
            print("I'm not running on a Pi.")
            
        self.re_init()
        self.set_window(0)
        self.clear()

        # Reset the damage arrays
        self.damage_rows = []
        
        for n in range(DAMAGE_ROWS):
            self.damage_rows.append([0] * VFD_WIDTH)

    def _wait_sbusy(self):
        # wait for GPIO to be free.  Modestly-inefficiently spin the CPU on this
        iters = 0
        
        while GPIO.input(23):
            time.sleep(0.001)
            iters += 1
        
        #print("SBUSY %d ms" % iters)
    
    def _send_command(self, byt):
        MAX_BYTES = 8
        
        #hx = ""
        #for b in byt:
        #    hx += "%02x " % b 
    
        if not AM_A_PI:
            return #print("Not a Pi.  Data:", hx)
        else:
            self._wait_sbusy()
            #print("I'm a Pi.  Data:", hx)
            
            # Write up to MAX_BYTES bytes at a time.  Anything left over, wait for SBUSY.
            while True:
                size = min(len(byt), MAX_BYTES)
                self.port.write(byt[0:size])
                #time.sleep(0.01)
                
                if size == MAX_BYTES:
                    byt = byt[size:]
                    self._wait_sbusy()
                else:
                    break
        
        self._wait_sbusy()

    def add_damage_region(self, x0, y0, x1, y1):
        print(x0, y0, x1, y1)
        x0 = clamp(x0, 0, VFD_WIDTH)
        x1 = clamp(x1, 0, VFD_WIDTH)

        if x0 > x1:
            x1, x0 = x0, x1

        y0 = clamp(y0, 0, VFD_HEIGHT)
        y1 = clamp(y1, 0, VFD_HEIGHT)

        if y0 > y1:
            y1, y0 = y0, y1
        
        damage_start = int(y0 / DAMAGE_ROW_HEIGHT)
        damage_end = int(y1 / DAMAGE_ROW_HEIGHT)

        # Two rows is all we support for now...
        if damage_start != damage_end:
            for x in range(x0, x1):
                self.damage_rows[0][x] = 1
                self.damage_rows[1][x] = 1
        else:
            for x in range(x0, x1):
                self.damage_rows[damage_start][x] = 1

    def clear_damage(self):
        for n in range(DAMAGE_ROWS):
            self.damage_rows[n] = [0] * VFD_WIDTH
    
    def text(self, font, x, y, str_, col=COL_WHITE):
        x, y = int(x), int(y)
        surf = font.render(str_, False, col)
        pos = (x, y)
        self.add_damage_region(pos[0], pos[1], pos[0] + surf.get_width(), pos[1] + surf.get_height())
        self.vfd_surf.blit(surf, dest=(x, y))

    def text_right(self, font, x, y, str_, col=COL_WHITE):
        x, y = int(x), int(y)
        surf = font.render(str_, False, col)
        pos = (self.vfd_surf.get_width() - surf.get_width() - x, y)
        self.add_damage_region(pos[0], pos[1], pos[0] + surf.get_width(), pos[1] + surf.get_height())
        self.vfd_surf.blit(surf, dest=pos)

    def line(self, x0, y0, x1, y1, w, col=COL_WHITE):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        self.add_damage_region(x0 - w + 1, y0 - w + 1, x1 + w - 1, y1 + w - 1)  # Approximate bounding box with line width
        pygame.draw.line(self.vfd_surf, col, (x0, y0), (x1, y1), w)

    def circle_inverse(self, x0, y0, r, w, col=COL_WHITE):
        x0, y0, r, w = int(x0), int(y0), int(r), int(w)
        self.add_damage_region(x0 - r - w + 1, y0 - r - w + 1, x0 + r + w - 1, y0 + r + w - 1)
        pygame.draw.circle(self.inv_surf, col, (x0, y0), r, w)

    def calculate_damage_list(self):
        # For each damage row, try to find a long contiguous string of 1s, indicating
        # a section is damaged.
        
        max_spacing = 4  # If less than 4 between this and adjacent runs, then break the runs up.
        rows = [[]] * DAMAGE_ROWS
        yn = 0
        
        for row in self.damage_rows:
            last_one = None
            runs = []
            run = []
            
            for n, x in enumerate(row):
                if x:
                    print(n, x)
                    if last_one != None and (n - last_one) > 4:
                        runs.append(run)
                        run = [n]
                    else:
                        run.append(n)
                        last_one = n

            run_ranges = []
            print(runs)
            
            for run in runs:
                run_ranges.append((run[0], run[-1]))
                pygame.display.rect(self.damage_surf, (255, 0, 0), (run[0], yn * DAMAGE_ROW_HEIGHT, run[-1] - run[0], DAMAGE_ROW_HEIGHT))
            
            rows[yn] = run_ranges
            yn += 1
        
        print(rows)
    
    def set_window(self, win):
        assert(win >= 0 and win <= 4)
        
        data = b"\x1F\x28\x77\x01"
        data += struct.pack("B", win)
        
        self._send_command(data)
        
    def re_init(self):
        self._send_command(bytes(b"\x1B\x40"))
    
    def clear(self):
        self._send_command(bytes(b"\x0C"))
    
    def set_cursor(self, x, y):
        # Set real cursor on display.  Y can be set with 8 pixel resolution.
        if (y & 0x07) > 0:
            raise ValueError("y not divisible by 8")

        y = int(y / 8)
        command = b"\x1F\x24" + struct.pack("@hh", x, y)
        self._send_command(bytes(command))

    def stream_out(self, surf, x0, y0, x1, y1):
        # Stream bitmap out from surface
        self.set_cursor(x0, y0)

        y0 = int(y0 / 8)
        y1 = int(y1 / 8)

        #print(y0, y1)
        
        command = b"\x1F\x28\x66\x11"
        command += struct.pack("@hh", x1 - x0 + 1, y1 - y0 + 1)  # append size
        command += b"\x01"

        # Pack image data, one row at a time
        a = pygame.surfarray.pixels3d(self.vfd_surf)
        
        rows = y1 - y0 + 1
        #print(rows)

        data = bytearray()
        yr = y0 * 8
        
        for r in range(rows):
            for x in range(x0, x1):
                byte = 0
                word = 0x80
                for yy in range(yr+0, yr+8):
                    if a[x][yy+(r*8)][0] != 0:
                        byte |= word
                    word >>= 1
                data.append(byte)
        
        #data = b"\x55\x00\x55\x00\x55\x00\x55\x00\x55\x00\x55"

        self._send_command(command + data + b"\x00")
    
    def render_out(self):
        # apply invert mask to the vfd_surf
        a = pygame.surfarray.pixels3d(self.vfd_surf)
        b = pygame.surfarray.pixels3d(self.inv_surf)
        self.vfd_surf = pygame.surfarray.make_surface(a ^ b)
        
        self.calculate_damage_list()
        self.clear_damage()
        
        # here we stream the surface to the Noritake VFD display
        if AM_A_PI:
            #self._send_command(b"Hello\r\n")
            #self._send_command(b"Hello\r\n")
            #self.clear()
            #self.stream_out(self.vfd_surf, 10 + (self.frame % 60), 0, 20 + (self.frame % 60), 0)
            self.stream_out(self.vfd_surf, 0, 0, 111, 7)
            self.stream_out(self.vfd_surf, 0, 8, 111, 15)
            time.sleep(0.01)

        # we also push it to the window and wait for the vsync
        if self.window != None:
            self.temp_surf.blit(self.vfd_surf, (0, 0))

            if ENABLE_DAMAGE_DEBUG:
                self.temp_surf.blit(self.damage_surf, (0, 0))
            
            pygame.transform.scale(self.temp_surf, self.window.get_size(), self.window)
            pygame.display.flip()

            # check if any events come through
            ev = pygame.event.poll()
            #print(ev)
            
            if ev.type == pygame.QUIT:
                print("Pygame quit!")
                pygame.display.quit()
                sys.exit()
                return False

        # clear the surfaces, back up old surface for diff
        self.last_vfd_surf.blit(self.vfd_surf, (0, 0))
        self.vfd_surf.fill((0, 0, 0))
        self.inv_surf.fill((0, 0, 0))
        self.damage_surf.fill((0, 0, 0, 0))
        
        self.frame += 1

        return True
