import pygame, sys, pprint, copy, time, struct

pygame.init()

DEMO_SCALE = 8
VFD_WIDTH = 112
VFD_HEIGHT = 16

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

class VFD(object):
    window = None
    vfd_surf = None
    last_vfd_surf = None
    frame = 0
    
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

    def _wait_sbusy(self):
        # wait for GPIO to be free.  Modestly-inefficiently spin the CPU on this
        iters = 0
        
        
        while GPIO.input(23):
            time.sleep(0.001)
            iters += 1
        
        print("SBUSY %d ms" % iters)
    
    def _send_command(self, byt):
        MAX_BYTES = 1
        
        hx = ""
        for b in byt:
            hx += "%02x " % b 
    
        if not AM_A_PI:
            print("Not a Pi.  Data:", hx)
        else:
            self._wait_sbusy()
            print("I'm a Pi.  Data:", hx)
            
            # Write up to MAX_BYTES bytes at a time.  Anything left over, wait for SBUSY.
            while True:
                size = min(len(byt), MAX_BYTES)
                self.port.write(byt[0:size])
                time.sleep(0.00025)
                
                if size == MAX_BYTES:
                    byt = byt[size+1:]
                    self._wait_sbusy()
                else:
                    break
        
    def text(self, font, x, y, str_, col=COL_WHITE):
        surf = font.render(str_, False, col)
        self.vfd_surf.blit(surf, dest=(x, y))

    def text_right(self, font, x, y, str_, col=COL_WHITE):
        surf = font.render(str_, False, col)
        self.vfd_surf.blit(surf, dest=(self.vfd_surf.get_width() - surf.get_width() - x, y))

    def line(self, x0, y0, x1, y1, w, col=COL_WHITE):
        pygame.draw.line(self.vfd_surf, col, (x0, y0), (x1, y1), w)

    def circle_inverse(self, x0, y0, r, w, col=COL_WHITE):
        pygame.draw.circle(self.inv_surf, col, (x0, y0), r, w)
    
    def arc_inverse(self, x0, y0, r, w, sa, ea, col=COL_WHITE):
        sa *= 3.14159/180.0
        ea *= 3.14159/180.0
        pygame.draw.arc(self.inv_surf, col, pygame.Rect((x0, y0), (r, r)), sa, ea, w)

    def calculate_damage_list(self):
        # List used to colorise the clusters for debugging
        t0 = time.time()
        
        cluster_cols = []
        for n in range(63, 255, 15):
            cluster_cols.append([n, 0, 0])
            cluster_cols.append([0, n, 0])
            cluster_cols.append([0, 0, n])
        working_cols = copy.copy(cluster_cols)
        
        # Check pixels from left to right and find the first non-matching pixel
        a = pygame.surfarray.pixels3d(self.vfd_surf)
        b = pygame.surfarray.pixels3d(self.last_vfd_surf)
        damage = []
        whole = False
        
        for y in range(0, VFD_HEIGHT):
            if whole: break
            for x in range(0, VFD_WIDTH):
                if whole: break
                if (a[x][y].all() != b[x][y].all()):
                    if (x, y) not in damage:
                        damage.append((x, y))

                        # Threshold >400 pixels changed, send the whole frame
                        if len(damage) > 400:
                            whole = True

        if whole:
            pygame.draw.rect(self.damage_surf, cluster_cols[0], (0, 0, VFD_WIDTH, VFD_HEIGHT))
            return [(0, 0, VFD_WIDTH, VFD_HEIGHT)]

        # Work through the damage list.  Arbitrarily pick the first pixel,
        # and try to find neighbours within a search_width x search_height block.
        # If a pixel is found, remove it from the damage list.  Add the bounding
        # box for damage pixels to the 'touched' list.  Iterate until there are
        # no pixels left in the damage list.
        clusters = []
        touched = []
        search_width = 8
        search_height = 8
        bboxes = []

        #print("There are %d damaged pixels" % len(damage))
        damage.sort(key=lambda x:(x[0]-x[1]))
        
        while (len(damage) > 0):
            ref = damage.pop()
            
            if ref not in touched:
                touched.append(ref)
                cluster = [ref]
            else:
                continue

            for adj in damage:
                # ignore touched pixels
                if adj in touched:
                    #print("Skipping", adj, "as already touched")
                    continue
                
                # trivial test: near to start coord?
                if abs(adj[0] - ref[0]) < search_width and abs(adj[1] - ref[1]) < search_height:
                    cluster.append(adj)
                    touched.append(adj)
                    damage.remove(adj) # O(n); could be O(1) at best
                else:
                    # if the pixel is close to other damage pixels, it becomes part of the same cluster
                    close = False
                    for pp in cluster:
                        #print("Dist:", abs(adj[0] - pp[0]), abs(adj[1] - pp[1]), adj, pp)
                        if abs(adj[0] - pp[0]) < search_width and abs(adj[1] - pp[1]) < search_height:
                            close = True
                            break

                    if close:
                        touched.append(adj)
                        cluster.append(adj)
                        damage.remove(adj) # O(n); could be O(1) at best

            #print("Got cluster of %d pixels" % len(cluster))
            #pprint.pp(touched)

            try:
                col = working_cols.pop()
            except IndexError:
                # ran out of colours, re-initialise list
                working_cols = copy.copy(cluster_cols)

            # find the bounding box of the cluster.  clusters must contain at least two pixels,
            # and cluster Y positions must start at 0 or 8
            if len(cluster) >= 2:
                x0 = cluster[0][0]
                y0 = cluster[0][1]
                x1 = cluster[1][0]
                y1 = cluster[1][1]
                
                for p in cluster:
                    if x0 > p[0]:
                        x0 = p[0]
                    if x1 < p[0]:
                        x1 = p[0]
                    if y0 > p[1]:
                        y0 = p[1]
                    if y1 < p[1]:
                        y1 = p[1]

                if (y0 % 8) != 0:
                    y0 = y0 & ~0x07
                    
                if (y1 % 8) != 0:
                    y1 = (y1 + 8) & ~0x07

                #pygame.draw.rect(self.damage_surf, col, (x0, y0, x1 - x0 + 1, y1 - y0 + 1))
                bboxes.append((x0, y0, x1, y1))

                # 'touch' all the pixels in this box
                for x in range(x0, x1 + 1):
                    for y in range(y0, y1 + 1):
                        self.damage_surf.set_at((x, y), col)
                        
                        if (x, y) not in touched:
                            touched.append((x, y))
                            
                        try:
                            damage.remove((x, y))
                        except:
                            pass
                            
            elif len(cluster) == 1:
                # not really a cluster is it, still needs to be handled
                x0 = cluster[0][0]
                y0 = cluster[0][1] & ~0x07
                y1 = y0 + 8

                for y in range(y0, y1):
                    self.damage_surf.set_at((x0, y), col)
                    touched.append((x, y))
                
                    try:
                        damage.remove((x, y))
                    except:
                        pass

                bboxes.append((x0, y0, x0, y1))

        t1 = time.time()
        #print("BBOX solve in %d ms" % ((t1 - t0) * 1000))
        return bboxes
    
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

        print(y0, y1)
        
        command = b"\x1F\x28\x66\x11"
        command += struct.pack("@hh", x1 - x0 + 1, y1 - y0 + 1)  # append size
        command += b"\x01"

        # Pack image data, one row at a time
        a = pygame.surfarray.pixels3d(self.vfd_surf)
        
        rows = y1 - y0 + 1
        print(rows)

        data = bytearray()
        
        for r in range(rows):
            for x in range(x0, x1):
                byte = 0
                word = 0x01
                for yy in range(0, 7):
                    if a[x][yy+(r*8)][0] != 0:
                        byte |= word
                    word <<= 1
                data.append(byte)
        
        #data = b"\x55\x00\x55\x00\x55\x00\x55\x00\x55\x00\x55"

        self._send_command(command + data)
    
    def render_out(self):
        # apply invert mask to the vfd_surf
        a = pygame.surfarray.pixels3d(self.vfd_surf)
        b = pygame.surfarray.pixels3d(self.inv_surf)
        self.vfd_surf = pygame.surfarray.make_surface(a ^ b)
        
        self.calculate_damage_list()
        
        # here we stream the surface to the Noritake VFD display
        if AM_A_PI:
            #self._send_command(b"Hello\r\n")
            #self._send_command(b"Hello\r\n")
            self.clear()
            #self.stream_out(self.vfd_surf, 10 + (self.frame % 60), 0, 20 + (self.frame % 60), 0)
            self.stream_out(self.vfd_surf, 0, 0, 111, 15)

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
