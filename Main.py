import Crypto_API
import VFD_Render
import pygame, time, locale, random, sys, math, datetime, os

RENDER_TO_WINDOW = True

ST_RENDER_A_COIN = 1
ST_TRANSITION = 2
ST_BRIGHTNESS = 3
ST_CLOCK = 4
ST_POWERDOWN = 5
ST_DATE_EVENT = 6

EV_BIRTHDAY = 1
EV_OTHER = 2

# Add coins you want to see here.
COINS = [
    # EnglishName   CodeName        ShortHand
    ('Shiba Inu',   'shiba-inu',    'SHIB'),
    ('Doge',        'dogecoin',     'DOGE'),
    ('Bitcoin',     'bitcoin',      'BTC'),
    ('Ethereum',    'ethereum',     'ETH'),
    ('Solana',      'solana',       'SOL'),
    ('Chia',        'chia',         'XCH'),
    ('Litecoin',    'litecoin',     'LTC'),
    ('Cardano',     'cardano',      'ADA')
]

# Add events you want to see here.
EVENTS = [
    # Text                      Type                Date (Year is ignored)
    ('Happy New Year!',         EV_OTHER,           datetime.date(1,  1,  1)),
    ('Happy Birthday Ross!',    EV_BIRTHDAY,        datetime.date(1,  8, 16)),
    ('Merry Christmas!',        EV_OTHER,           datetime.date(1, 12, 25)),
    ('Test Event!',             EV_OTHER,           datetime.date(1, 12, 19))
]

# Day of week names.  Why would you change these?
DAY_OF_WEEK = ['Mon', 'Tues', 'Wed', 'Thur', 'Fri', 'Sat', 'Sun']

def money_fmt_nodec(prefix, suffix, val):
    return prefix + locale.format_string("%.0f", val, grouping=True, monetary=False) + suffix

def usd_fmt_nodec(val):
    if val < 0.1:
        return locale.format_string("%.4f", val * 100, grouping=True, monetary=False) + "¢"
    elif val < 10:
        return locale.format_string("%.2f", val * 100, grouping=True, monetary=False) + "¢"
    elif val < 100:
        return "$" + locale.format_string("%.3f", val, grouping=True, monetary=False)
    elif val < 1000:
        return "$" + locale.format_string("%.2f", val, grouping=True, monetary=False)
    elif val < 10000:
        return "$" + locale.format_string("%.0f", val, grouping=True, monetary=False)
    elif val < 100000:
        return "$" + locale.format_string("%.2f", val / 1000, grouping=True, monetary=False) + "k"
    elif val < 10000000:
        return "$" + locale.format_string("%.1f", val / 1000, grouping=True, monetary=False) + "k"
    elif val < 10000000000:
        return "$" + locale.format_string("%.1f", val / 1000000, grouping=True, monetary=False) + "M"

def sign_fmt_dec(prefix, suffix, val):
    if abs(val) < 10:
        # 2 D.P.
        return prefix + locale.format_string("%+.2f", val, grouping=True, monetary=False) + suffix
    elif abs(val) < 100:
        # 1 D.P.
        return prefix + locale.format_string("%+.1f", val, grouping=True, monetary=False) + suffix
    elif abs(val) < 1000:
        return prefix + locale.format_string("%+.0f", val, grouping=True, monetary=False) + suffix
    elif abs(val) < 10000:
        return prefix + locale.format_string("%+.2f", val / 1000, grouping=True, monetary=False) + "k" + suffix
    elif abs(val) < 100000:
        return prefix + locale.format_string("%+.1f", val / 1000, grouping=True, monetary=False) + "k" + suffix
    elif abs(val) < 1000000:
        return prefix + locale.format_string("%+.0f", val / 1000, grouping=True, monetary=False) + "k" + suffix
    elif abs(val) < 10000000:
        return prefix + locale.format_string("%+.2f", val / 1000000, grouping=True, monetary=False) + "M" + suffix
    elif abs(val) < 100000000:
        return prefix + locale.format_string("%+.1f", val / 1000000, grouping=True, monetary=False) + "M" + suffix
    elif abs(val) < 1000000000:
        return prefix + locale.format_string("%+.0f", val / 1000000, grouping=True, monetary=False) + "M" + suffix

def nosign_fmt_dec(prefix, suffix, val):
    if abs(val) < 10:
        # 2 D.P.
        return prefix + locale.format_string("%.3f", val, grouping=True, monetary=False) + suffix
    elif abs(val) < 100:
        # 1 D.P.
        return prefix + locale.format_string("%.2f", val, grouping=True, monetary=False) + suffix
    elif abs(val) < 1000:
        return prefix + locale.format_string("%.1f", val, grouping=True, monetary=False) + suffix
    elif abs(val) < 10000:
        return prefix + locale.format_string("%.3f", val / 1000, grouping=True, monetary=False) + "k" + suffix
    elif abs(val) < 100000:
        return prefix + locale.format_string("%.2f", val / 1000, grouping=True, monetary=False) + "k" + suffix
    elif abs(val) < 1000000:
        return prefix + locale.format_string("%.1f", val / 1000, grouping=True, monetary=False) + "k" + suffix
    elif abs(val) < 10000000:
        return prefix + locale.format_string("%.3f", val / 1000000, grouping=True, monetary=False) + "M" + suffix
    elif abs(val) < 100000000:
        return prefix + locale.format_string("%.2f", val / 1000000, grouping=True, monetary=False) + "M" + suffix
    elif abs(val) < 1000000000:
        return prefix + locale.format_string("%.1f", val / 1000000, grouping=True, monetary=False) + "M" + suffix
    elif abs(val) < 10000000000:
        return prefix + locale.format_string("%.3f", val / 1000000000, grouping=True, monetary=False) + "B" + suffix
    elif abs(val) < 100000000000:
        return prefix + locale.format_string("%.2f", val / 1000000000, grouping=True, monetary=False) + "B" + suffix
    elif abs(val) < 1000000000000:
        return prefix + locale.format_string("%.1f", val / 1000000000, grouping=True, monetary=False) + "B" + suffix
    elif abs(val) < 10000000000000:
        return prefix + locale.format_string("%.3f", val / 1000000000000, grouping=True, monetary=False) + "T" + suffix
    elif abs(val) < 100000000000000:
        return prefix + locale.format_string("%.2f", val / 1000000000000, grouping=True, monetary=False) + "T" + suffix
    elif abs(val) < 1000000000000000:
        return prefix + locale.format_string("%.1f", val / 1000000000000, grouping=True, monetary=False) + "T" + suffix

class Main(object):
    vfd = None
    clk = None
    f = 0
    real_fps = 0
    state = ST_DATE_EVENT
    disp_state = ST_RENDER_A_COIN
    current_coin = None
    cd = None
    arrow = 0
    transition = 0
    effect = 0
    bri_state = 0
    vfd_bright = 7
    pd_state = 0
    date_event = EVENTS[0]

    def __init__(self):
        self.vfd = VFD_Render.VFD(RENDER_TO_WINDOW)
        self.clk = pygame.time.Clock()
        self.cf = Crypto_API.CryptoFetch()
        self.cf.start()
        locale.setlocale(locale.LC_ALL, '')

        # Set the arrow functions up
        self.arrow_up = [self.render_arrow_up_rotate, self.render_arrow_up_scroll, self.render_arrow_up_flash]
        self.arrow_down = [self.render_arrow_down_rotate, self.render_arrow_down_scroll, self.render_arrow_down_flash]

        # Add the coins
        for coin in COINS:
            self.cf.add_monitor(coin[0], coin[1], coin[2])

        # Start with first coin
        self.current_coin = COINS[0][1]

        # Load fonts
        self.big_font = pygame.font.Font("BebasNeue-Regular.ttf", 19)
        self.small_font = pygame.font.Font("RosesareFF0000.ttf", 8)
        
        # Set default brightness (@FUTURE: Load config file!)
        self.vfd.set_disp_bright(self.vfd_bright)

    def render_arrow_up_rotate(self, x, f):
        f %= 32
        f &= ~0x03
        f += 4
        if f > 16:
            f = 32 - f
        
        self.vfd.line(x, 0, x - (f / 2), 8, 1)
        self.vfd.line(x, 0, x + (f / 2), 8, 1)
        self.vfd.line(x - (f / 2), 8, x - (f / 4), 8, 1)
        self.vfd.line(x + (f / 2), 8, x + (f / 4), 8, 1)
        self.vfd.line(x + (f / 4), 8, x + (f / 4), 15, 1)
        self.vfd.line(x - (f / 4), 8, x - (f / 4), 15, 1)
        self.vfd.line(x - (f / 4), 15, x + (f / 4), 15, 1)
        
    def render_arrow_up_scroll(self, x, f):
        f %= 40
        w = 16
        y = 32 - (f + 16)
        
        self.vfd.line(x, y, x - (w / 2), 8 + y, 1)
        self.vfd.line(x, y, x + (w / 2), 8 + y, 1)
        self.vfd.line(x - (w / 2), 8 + y, x - (w / 4), 8 + y, 1)
        self.vfd.line(x + (w / 2), 8 + y, x + (w / 4), 8 + y, 1)
        self.vfd.line(x + (w / 4), 8 + y, x + (w / 4), 15 + y, 1)
        self.vfd.line(x - (w / 4), 8 + y, x - (w / 4), 15 + y, 1)
        self.vfd.line(x - (w / 4), 15 + y, x + (w / 4), 15 + y, 1)
        
    def render_arrow_up_flash(self, x, f):
        f %= 100
        w = 16
        y = 0
        cols = [(255,255,255), (0,0,0)]
        col = cols[int((f / 24) % 2)]
        
        self.vfd.line(x, y, x - (w / 2), 8 + y, 1, col)
        self.vfd.line(x, y, x + (w / 2), 8 + y, 1, col)
        self.vfd.line(x - (w / 2), 8 + y, x - (w / 4), 8 + y, 1, col)
        self.vfd.line(x + (w / 2), 8 + y, x + (w / 4), 8 + y, 1, col)
        self.vfd.line(x + (w / 4), 8 + y, x + (w / 4), 15 + y, 1, col)
        self.vfd.line(x - (w / 4), 8 + y, x - (w / 4), 15 + y, 1, col)
        self.vfd.line(x - (w / 4), 15 + y, x + (w / 4), 15 + y, 1, col)
        
    def render_arrow_down_rotate(self, x, f):
        f %= 32
        f &= ~0x03
        f += 4
        if f > 16:
            f = 32 - f
        y = 0
        
        self.vfd.line(x, 15 - y, x - (f / 2), 7 - y, 1)
        self.vfd.line(x, 15 - y, x + (f / 2), 7 - y, 1)
        self.vfd.line(x - (f / 2), 7 - y, x - (f / 4), 7 - y, 1)
        self.vfd.line(x + (f / 2), 7 - y, x + (f / 4), 7 - y, 1)
        self.vfd.line(x + (f / 4), 0 - y, x + (f / 4), 7 - y, 1)
        self.vfd.line(x - (f / 4), 0 - y, x - (f / 4), 7 - y, 1)
        self.vfd.line(x - (f / 4), 0 - y, x + (f / 4), 0 - y, 1)
        
    def render_arrow_down_scroll(self, x, f):
        f %= 40
        w = 16
        y = 32 - (f + 16)
        
        self.vfd.line(x, 16 - y, x - (w / 2), 8 - y, 1)
        self.vfd.line(x, 16 - y, x + (w / 2), 8 - y, 1)
        self.vfd.line(x - (w / 2), 8 - y, x - (w / 4), 8 - y, 1)
        self.vfd.line(x + (w / 2), 8 - y, x + (w / 4), 8 - y, 1)
        self.vfd.line(x + (w / 4), 0 - y, x + (w / 4), 8 - y, 1)
        self.vfd.line(x - (w / 4), 0 - y, x - (w / 4), 8 - y, 1)
        self.vfd.line(x - (w / 4), 0 - y, x + (w / 4), 0 - y, 1)
        
    def render_arrow_down_flash(self, x, f):
        f %= 100
        w = 16
        y = 0
        cols = [(255,255,255), (0,0,0)]
        col = cols[int((f / 24) % 2)]
        
        self.vfd.line(x, 15 - y, x - (w / 2), 7 - y, 1, col)
        self.vfd.line(x, 15 - y, x + (w / 2), 7 - y, 1, col)
        self.vfd.line(x - (w / 2), 7 - y, x - (w / 4), 7 - y, 1, col)
        self.vfd.line(x + (w / 2), 7 - y, x + (w / 4), 7 - y, 1, col)
        self.vfd.line(x + (w / 4), 0 - y, x + (w / 4), 7 - y, 1, col)
        self.vfd.line(x - (w / 4), 0 - y, x - (w / 4), 7 - y, 1, col)
        self.vfd.line(x - (w / 4), 0 - y, x + (w / 4), 0 - y, 1, col)

    def render_invert_concentric_circles(self, x, f):
        f %= 200
        self.vfd.circle_inverse(x, 8, f + 7, 7)
        self.vfd.circle_inverse(x, 8, f + 14, 7)

    def render_invert_slices(self, x, f):
        pass

    def check_data_ready(self):
        c_data = self.cf.get_coin(self.current_coin)

        if (time.time() - c_data.updateTime) > 240:
            print("Data not ready: %s! f=%d" % (self.current_coin, self.f))
            self.vfd.fill(VFD_Render.COL_WHITE)
            self.vfd.text(self.small_font, 200 - (self.f % 400), 4, "Waiting for data (%s)" % self.current_coin, col=VFD_Render.COL_BLACK)
            return False
        else:
            return True
        
    def render_a_coin(self):
        c_data = self.cf.get_coin(self.current_coin)

        if len(c_data._fname) > 6:
            self.vfd.text(self.small_font, 0, 0, c_data._code)
        else:
            self.vfd.text(self.small_font, 0, 0, c_data._fname)

        # Show alternating text
        f_sub = int(self.f % 600)
        
        if f_sub < 50:
            self.vfd.text(self.small_font, 0, 9, "24h")
        elif f_sub < 125:
            self.vfd.text(self.small_font, 0, 9, "Chg$")
        elif f_sub < 275:
            self.vfd.text(self.small_font, 0, 9, sign_fmt_dec("", "%", c_data.priceUSDChange24Hr))
        elif f_sub < 400:
            self.vfd.text(self.small_font, 0, 9, "24h")
        elif f_sub < 500:
            self.vfd.text(self.small_font, 0, 9, "Vol$")
        elif f_sub < 575:
            self.vfd.text(self.small_font, 0, 9, nosign_fmt_dec("", "", c_data.volumeUSD))
        
        self.vfd.text_right(self.big_font, 0, -3, usd_fmt_nodec(c_data.lastPriceUSD))
        
        if c_data.priceUSDChange24Hr > 0:
            self.arrow_up[self.arrow](45, self.f)
        elif c_data.priceUSDChange24Hr < 0:
            self.arrow_down[self.arrow](45, self.f)

        if self.effect == 0:
            if 200 < self.f < 400:
                self.render_invert_concentric_circles(120, self.f - 200)
        elif self.effect == 1:
            if 200 < self.f < 400:
                self.render_invert_slices(-10, self.f - 200)

    def animate_next_coin_start(self):
        self.f = 0
        self.vfd.save_surface()
        self.next_coin()
        self.state = ST_TRANSITION
        self.transition = random.choice([0, 1])
        self.effect = random.choice([0, 1, 2])
        self.date_event = None
        
        # Use this chance to show an event if our 'roll of dice' results in that.
        self.do_event = random.choice([0, 1, 2, 3, 4, 5])
        if self.do_event == 0:
            # Any matching events?
            if self.choose_date_event():
                self.state = ST_DATE_EVENT
    
    def choose_date_event(self):
        now = datetime.datetime.now()
        candidates = []
        
        # Try to find a matching event
        for ev in EVENTS:
            if ev[2].month == now.month and ev[2].day == now.day:
                candidates.append(ev)
        
        if len(candidates) > 0:
            self.date_event = random.choice(candidates)
            return True
        else:
            self.date_event = None
            return False
    
    def render_brightness(self):
        if self.bri_state != 0:
            self.vfd_bright += self.bri_state
            self.vfd_bright = VFD_Render.clamp(self.vfd_bright, 0, 7)
            self.vfd.set_disp_bright(self.vfd_bright)
            self.bri_state = 0
        
        # Draw 'N' filled or unfilled boxes of height stepping up 1pix every time
        for n in range(8):
            if n <= self.vfd_bright:
                lw = 0
            else:
                lw = 1
            
            self.vfd.rect(30 + (8 * n), 10 - n, 7, n + 4, lw, VFD_Render.COL_WHITE)
        
        self.vfd.text_right(self.big_font, 0, -3, "%d" % (1 + self.vfd_bright))
        
        # Draw brightness symbol
        cx, cy = 11, 7
        xb = yb = 6
        xc = yc = 7
        r = 3
        
        self.vfd.line(cx - xb, cy - yb, cx + xb, cy + yb, 1, VFD_Render.COL_WHITE)
        self.vfd.line(cx + xb, cy - yb, cx - xb, cy + yb, 1, VFD_Render.COL_WHITE)
        self.vfd.line(cx + xc, cy,      cx - xc, cy,      1, VFD_Render.COL_WHITE)
        self.vfd.line(cx,      cy - yc, cx,      cy + yc, 1, VFD_Render.COL_WHITE)
        self.vfd.circle_filled(cx, cy, r, VFD_Render.COL_BLACK)
        self.vfd.circle(cx, cy, r, VFD_Render.COL_WHITE)
        self.vfd.circle(cx, cy, 5, VFD_Render.COL_WHITE)
        self.vfd.circle(cx, cy, r + 1, VFD_Render.COL_BLACK)
        self.vfd.circle(cx, cy, r + 2, VFD_Render.COL_BLACK)
    
    def render_clock(self):
        # Get the time
        dt = datetime.datetime.now()
        
        # Draw time.  Blink the dots on 0.5 sec intervals
        dots = (time.time() % 1.0) >= 0.5
        self.vfd.text_right(self.big_font, 5, -3, "%02d" % dt.second)
        self.vfd.text_right(self.big_font, 30, -3, "%02d" % dt.minute)
        self.vfd.text_right(self.big_font, 55, -3, "%02d" % dt.hour)
        
        if dots:
            self.vfd.text_right(self.big_font, 23, -5, ":")
            self.vfd.text_right(self.big_font, 48, -5, ":")
        
        # Draw date.
        self.vfd.text(self.small_font, 0, 0, DAY_OF_WEEK[dt.weekday()])
        self.vfd.text(self.small_font, 0, 9, "%d %s" % (dt.day, dt.strftime('%b')))
    
    def render_date_event(self):
        # Render the date-event.
        ev = self.date_event
        
        # Draw the characters in a wave
        self.vfd.text_wave(self.small_font, -150 + (self.f % 400), 1, ev[0], self.f * 0.02, 7)
        self.vfd.line(VFD_Render.VFD_WIDTH - 1, 0, VFD_Render.VFD_WIDTH - 1, VFD_Render.VFD_HEIGHT - 1, 1, VFD_Render.COL_BLACK)
        self.vfd.line(0, 0, 0, VFD_Render.VFD_HEIGHT - 1, 1, VFD_Render.COL_BLACK)
    
    def render_powerdown(self):
        if self.pd_state == 0:
            if (self.f / 10) % 4 < 3:
                self.vfd.text(self.small_font, 0, 0, "To power off")
            
            self.vfd.text(self.small_font, 0, 9, "hold 'X' down again")
        elif self.pd_state == 1:
            # Does nothing
            pass
    
    def render_frame(self):
        if self.state == ST_RENDER_A_COIN:
            if self.check_data_ready():
                self.render_a_coin()

            if (self.f % 1300) > 1200:
                self.animate_next_coin_start()
            
            self.disp_state = ST_RENDER_A_COIN
        elif self.state == ST_TRANSITION:
            if self.check_data_ready():
                self.render_a_coin()
            
            if self.transition == 0:
                self.vfd.transition_scroll(int(self.f * 3.5))
                if self.f > 50:
                    self.state = ST_RENDER_A_COIN
                    self.f = 0
            elif self.transition == 1:
                self.vfd.transition_dissolve(25 - self.f)
                if self.f > 25:
                    self.state = ST_RENDER_A_COIN
                    self.f = 0
            else:
                self.state = ST_RENDER_A_COIN
        elif self.state == ST_BRIGHTNESS:
            self.render_brightness()
            
            if self.f > 100:
                self.state = self.disp_state
        elif self.state == ST_CLOCK:
            self.render_clock()
            self.disp_state = ST_CLOCK
        elif self.state == ST_DATE_EVENT:
            self.render_date_event()
            
            if self.f > 400:
                self.state = self.disp_state
        elif self.state == ST_POWERDOWN:
            self.render_powerdown()
            
            if self.f > 500:
                self.state = self.disp_state
    
    def initiate_shutdown(self):
        self.state = ST_POWERDOWN
        self.pd_state = 0
    
    def handle_event(self, ev):
        print("Event %04x (%d)" % (ev, ev))
        
        # Actions:
        #  - Press A:  Next coin
        #  - Press B:  Change display
        #  - Press X:  Change brightness up
        #  - Press Y:  Change brightness down
        #  - Hold Y:   Prompt to shut down
        if ev & VFD_Render.EV_SW_A_RELEASE:
            self.animate_next_coin_start()
            return
        
        if ev & VFD_Render.EV_SW_B_RELEASE:
            # If we're on Coin, switch to Clock
            if self.state == ST_RENDER_A_COIN:
                self.state = ST_CLOCK
            elif self.state == ST_CLOCK:
                self.state = ST_RENDER_A_COIN
        
        if ev & VFD_Render.EV_SW_X_RELEASE:
            if self.state != ST_POWERDOWN:
                self.f = 0
                self.state = ST_BRIGHTNESS
                self.bri_state = +1
        
        if ev & VFD_Render.EV_SW_Y_RELEASE:
            if self.state != ST_POWERDOWN:
                self.f = 0
                self.state = ST_BRIGHTNESS
                self.bri_state = -1
        
        if ev & VFD_Render.EV_SW_Y_HOLD:
            if self.pd_state == 0:
                self.initiate_shutdown()
                self.pd_state = 1
            elif self.pd_state == 1:
                print("Now shutting down...")
                os.system("shutdown now")
    
    def next_coin(self):
        self.arrow = random.choice([0, 1, 2])
        
        for i in range(len(COINS)):
            if COINS[i][1] == self.current_coin:
                break

        i += 1
        i %= len(COINS)
        self.current_coin = COINS[i][1]

    def run(self):
        self.render_frame()
        ev = self.vfd.render_out()
        
        if ev == False:
            self.cf.kill()
            return False
        else:
            if ev != VFD_Render.EV_NONE:
                self.handle_event(ev)
        
        self.f += 1
        self.f %= 1000000

        # Get any API updates asynchronously
        self.cf.update()

        if self.f % 30 == 0:
            print("tick", self.real_fps, self.f)
            
        self.real_fps = 1.0 / self.clk.tick(30)
        return True

if __name__ == "__main__":
    m = Main()

    while True:
        if not m.run():
            break

    print("Quitting")
    sys.exit()
    
