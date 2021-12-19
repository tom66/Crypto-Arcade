import pygame, sys, pprint, copy, time, struct, numpy, random, math
import pygame.gfxdraw

pygame.init()

DEMO_SCALE = 8
VFD_WIDTH = 112
VFD_HEIGHT = 16
DAMAGE_ROWS = 2
DAMAGE_ROW_HEIGHT = 8

COL_WHITE = (255, 255, 255)
COL_BLACK = (0, 0, 0)

ENABLE_DAMAGE_DEBUG = True

EV_SW_X_ACTIVATE    = 1
EV_SW_Y_ACTIVATE    = 2
EV_SW_A_ACTIVATE    = 4
EV_SW_B_ACTIVATE    = 8
EV_SW_X_HOLD        = 16
EV_SW_Y_HOLD        = 32
EV_SW_A_HOLD        = 64
EV_SW_B_HOLD        = 128
EV_SW_X_RELEASE     = 256
EV_SW_Y_RELEASE     = 512
EV_SW_A_RELEASE     = 1024
EV_SW_B_RELEASE     = 2048
EV_NONE             = 65536

HOLD_THRESH         = 20

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
    vfd_surfarray = None
    last_vfd_surf = None
    frame = 0
    old_bytes = []
    new_bytes = []
    
    sw_x_last = 0
    sw_y_last = 0
    sw_a_last = 0
    sw_b_last = 0
    
    sw_x_ctr = 0
    sw_y_ctr = 0
    sw_a_ctr = 0
    sw_b_ctr = 0
    
    sw_state = EV_NONE
    
    def __init__(self, render_window):
        if render_window:
            self.window = pygame.display.set_mode(size=(VFD_WIDTH * DEMO_SCALE, VFD_HEIGHT * DEMO_SCALE))
        else:
            self.window = None
            
        self.vfd_surf = pygame.Surface(size=(VFD_WIDTH, VFD_HEIGHT))
        self.vfd_surf.fill((0, 0, 0))
            
        self.saved_vfd_surf = pygame.Surface(size=(VFD_WIDTH, VFD_HEIGHT))
        self.saved_vfd_surf.fill((0, 0, 0))
            
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
            GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
            GPIO.setup(19, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
            GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
            GPIO.setup(6,  GPIO.IN, pull_up_down=GPIO.PUD_UP) 
            self.port = serial.Serial(port="/dev/ttyS0", baudrate=115200)
        else:
            print("I'm not running on a Pi.")
            
        self.re_init()
        self.set_window(0)
        self.clear()

        self.my_random = random.Random(0)

        # Reset the damage arrays
        self.old_bytes = []
        self.new_bytes = []
        
        for n in range(DAMAGE_ROWS):
            self.old_bytes.append([0x00] * VFD_WIDTH)
            self.new_bytes.append([0x00] * VFD_WIDTH)
    
    def scan_gpio(self):
        if not AM_A_PI:
            return EV_NONE
        
        ev = 0
        
        # check the new state and compare it to the old one
        # states are inverted
        x = 1 - GPIO.input(19)
        y = 1 - GPIO.input(26)
        a = 1 - GPIO.input(6)
        b = 1 - GPIO.input(13)
        
        if x and not self.sw_x_last:
            ev |= EV_SW_X_ACTIVATE
        if y and not self.sw_y_last:
            ev |= EV_SW_Y_ACTIVATE
        if a and not self.sw_a_last:
            ev |= EV_SW_A_ACTIVATE
        if b and not self.sw_b_last:
            ev |= EV_SW_B_ACTIVATE
        
        if not x and self.sw_x_last:
            ev |= EV_SW_X_RELEASE
        if not y and self.sw_y_last:
            ev |= EV_SW_Y_RELEASE
        if not a and self.sw_a_last:
            ev |= EV_SW_A_RELEASE
        if not b and self.sw_b_last:
            ev |= EV_SW_B_RELEASE
        
        if x:
            self.sw_x_ctr += 1
            if self.sw_x_ctr == HOLD_THRESH:
                ev |= EV_SW_X_HOLD
        else:
            self.sw_x_ctr = 0
            
        if y:
            self.sw_y_ctr += 1
            if self.sw_y_ctr == HOLD_THRESH:
                ev |= EV_SW_Y_HOLD
        else:
            self.sw_y_ctr = 0
            
        if a:
            self.sw_a_ctr += 1
            if self.sw_a_ctr == HOLD_THRESH:
                ev |= EV_SW_A_HOLD
        else:
            self.sw_a_ctr = 0
            
        if b:
            self.sw_b_ctr += 1
            if self.sw_b_ctr == HOLD_THRESH:
                ev |= EV_SW_B_HOLD
        else:
            self.sw_b_ctr = 0
        
        self.sw_x_last = x
        self.sw_y_last = y
        self.sw_a_last = a
        self.sw_b_last = b
        
        #print("x/y/a/b", x, y, a, b)
        
        if ev == 0:
            ev |= EV_NONE
        
        return ev
    
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
    
    def text(self, font, x, y, str_, col=COL_WHITE):
        x, y = int(x), int(y)
        surf = font.render(str_, False, col)
        pos = (x, y)
        #print(surf, "blit", str_, x, y, col)
        self.vfd_surf.blit(surf, dest=(x, y))

    def text_right(self, font, x, y, str_, col=COL_WHITE):
        x, y = int(x), int(y)
        surf = font.render(str_, False, col)
        pos = (self.vfd_surf.get_width() - surf.get_width() - x, y)
        self.vfd_surf.blit(surf, dest=pos)

    def text_wave(self, font, x, y, str_, phase, ampl, col=COL_WHITE):
        xx = x
        for n, ch in enumerate(str_):
            surf = font.render(ch, False, col)
            h = surf.get_height()
            for p in range(surf.get_width()):
                q = n + p
                yy = int(y + (ampl * math.sin(((xx + p) * 0.06) + phase)))
                self.vfd_surf.blit(surf, dest=(xx + p, yy), area=(p, 0, 1, h))
            xx += surf.get_width()
        
    def line(self, x0, y0, x1, y1, w, col=COL_WHITE):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        pygame.draw.line(self.vfd_surf, col, (x0, y0), (x1, y1), w)
    
    def rect(self, x0, y0, w, h, lw, col=COL_WHITE):
        pygame.draw.rect(self.vfd_surf, col, (x0, y0, w, h), lw)
    
    def circle(self, x0, y0, r, col=COL_WHITE):
        x0, y0, r = int(x0), int(y0), int(r)
        pygame.gfxdraw.circle(self.vfd_surf, x0, y0, r, col)
        
    def circle_filled(self, x0, y0, r, col=COL_WHITE):
        x0, y0, r = int(x0), int(y0), int(r)
        pygame.gfxdraw.filled_circle(self.vfd_surf, x0, y0, r, col)
    
    def circle_inverse(self, x0, y0, r, w, col=COL_WHITE):
        x0, y0, r, w = int(x0), int(y0), int(r), int(w)
        pygame.draw.circle(self.inv_surf, col, (x0, y0), r, w)

    def fill(self, col=COL_BLACK):
        self.vfd_surf.fill(col)

    def calculate_damage_list(self):
        # Compute the byte arrays for each row.
        min_runlength = 15  # Runlength should be size of one move command + one bitmap header
        a = self.vfd_surfarray

        packed = numpy.packbits(a, axis=1)
        
        for y in range(DAMAGE_ROWS):
            self.new_bytes[y] = packed[:, y, 0]

        # For each damage row, try to find a long contiguous string of disagreeing bytes, indicating
        # a section is damaged.
        
        max_spacing = 4  # If less than 4 between this and adjacent runs, then break the runs up.
        rows = [[]] * DAMAGE_ROWS
        yp = 0
        
        for yn, row in enumerate(self.new_bytes):
            last_row = self.old_bytes[yn]
            last_one = None
            runs = []
            run = []
            
            for n, (past, pres) in enumerate(zip(last_row, row)):
                if past != pres:
                    if last_one != None and (n - last_one) > min_runlength:
                        runs.append(run)
                        run = [n]
                        last_one = n
                    else:
                        run.append(n)
                        last_one = n

            if len(run) > 0:
                runs.append(run)  # Pack last run, if any.
            
            run_ranges = []
            #print("runs:", runs)
            
            for run in runs:
                run_ranges.append((run[0], clamp(run[-1] + 1, 0, VFD_WIDTH - 1)))
            
            rows[yn] = run_ranges
            yp += DAMAGE_ROW_HEIGHT

        # update the state
        #print("id?", self.old_bytes == self.new_bytes)
        self.old_bytes = copy.deepcopy(self.new_bytes)
        
        return rows
    
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
        #print("set_cursor(%r,%r)" % (x, y))
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
        
        command = b"\x1F\x28\x66\x11"
        command += struct.pack("@hh", x1 - x0, y1 - y0)  # append size
        command += b"\x01"

        # Pack image data, one row at a time.  Use cached values if available, and update
        # the cache as we go.
        data = bytearray()
        
        for r in range(y0, y1 + 1):
            yp = r * DAMAGE_ROW_HEIGHT
            pygame.draw.rect(self.damage_surf, (255, 0, 0), (x0, yp, x1 - x0, DAMAGE_ROW_HEIGHT))
            
            for n in range(x0, x1):
                data.append(self.new_bytes[r][n])

        self._send_command(command + data)
    
    def set_disp_bright(self, bri):
        # Input level 0-7, out of range values clipped.  Actual brightness levels are 1-8 for the VFD.
        bri = clamp(bri, 0, 7) + 1
        
        command = b"\x1F\x58"
        command += struct.pack("b", bri)
        
        self._send_command(command)
    
    def save_surface(self):
        # Save the current VFD surface so a transition/effect can be applied.
        self.saved_vfd_surf.blit(self.vfd_surf, (0, 0))

    def transition_scroll(self, amt):
        # Blit the old surface onto the new surface and scroll it away with a line
        self.vfd_surf.blit(self.saved_vfd_surf, (amt, 0), area=(amt, 0, VFD_WIDTH - clamp(amt, 0, VFD_WIDTH), VFD_HEIGHT))
        self.line(amt, 0, amt, VFD_HEIGHT, 20, COL_WHITE)

    def transition_dissolve(self, amt):
        self.my_random.seed(0)
        
        # blocks of NxN pixels on a grid are allocated to be old or new, with a higher 'amt' figure determining more new than old.
        allocs = []
        blkwidth = 4
        blkheight = 4
        nx, ny = None, None

        # maximum allocs
        maxallocs = ((VFD_WIDTH / blkwidth) * (VFD_HEIGHT / blkheight)) - 1
        
        for i in range(amt * 5):
            while True:
                nx = self.my_random.randrange(0, VFD_WIDTH / blkwidth)
                ny = self.my_random.randrange(0, VFD_HEIGHT / blkheight)
                if (nx, ny) in allocs:
                    continue
                if len(allocs) >= maxallocs:
                    break
                allocs.append((nx, ny))
                self.vfd_surf.blit(self.saved_vfd_surf, (nx * blkwidth, ny * blkheight), area=(nx * blkwidth, ny * blkheight, blkwidth, blkheight))
                break

        #print(amt, allocs)
    
    def render_out(self):
        # apply invert mask to the vfd_surf
        a = pygame.surfarray.pixels3d(self.vfd_surf)
        b = pygame.surfarray.pixels3d(self.inv_surf)
        self.vfd_surfarray = a ^ b
        self.vfd_surf = pygame.surfarray.make_surface(self.vfd_surfarray)

        t0 = time.time()
        rows = self.calculate_damage_list()
        t1 = time.time()
        
        self.sw_state = EV_NONE

        #print((t1 - t0) * 1000)
        
        # here we stream the surface to the Noritake VFD display
        if AM_A_PI:
            # Sort data by X.
            row_data = []
            for y, row in enumerate(rows):
                for r in row:
                    row_data.append((r[0], r[1], y))

            row_data = row_data.sort(key=lambda r: r[0])
            
            for y, row in enumerate(rows):
                for r in row:
                    #print("rowdata:", r)
                    self.stream_out(self.vfd_surf, r[0], y * DAMAGE_ROW_HEIGHT, r[1], (y * DAMAGE_ROW_HEIGHT) + DAMAGE_ROW_HEIGHT - 1)

        # we also push it to the window and wait for the vsync
        if self.window != None:
            self.temp_surf.blit(self.vfd_surf, (0, 0))

            if ENABLE_DAMAGE_DEBUG:
                self.temp_surf.blit(self.damage_surf, (0, 0))
            
            pygame.transform.scale(self.temp_surf, self.window.get_size(), self.window)
            pygame.display.flip()

            # check if any PyGame events come through
            ev = pygame.event.poll()
            #print(ev)
            
            if ev.type == pygame.QUIT:
                print("Pygame quit!")
                pygame.display.quit()
                sys.exit()
                return False
            
            # scan for GPIO events every frame
            if AM_A_PI:
                self.sw_state = self.scan_gpio()

        # clear the surfaces, back up old surface for diff
        self.last_vfd_surf.blit(self.vfd_surf, (0, 0))
        self.vfd_surf.fill((0, 0, 0))
        self.inv_surf.fill((0, 0, 0))
        self.damage_surf.fill((0, 0, 0, 0))
        self.frame += 1

        return self.sw_state
