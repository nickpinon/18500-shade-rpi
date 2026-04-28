import time
import lgpio

STEP_PIN = 17
DIR_PIN = 27
EN_PIN = 22

# Faster speed: 1000Hz (1ms period)
# At 1000Hz, the output shaft will move at ~0.1 RPM (still slow, but visible!)
STEP_DELAY = 0.0005 

def run_test():
    chip = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(chip, STEP_PIN, 0)
    lgpio.gpio_claim_output(chip, DIR_PIN, 0)
    lgpio.gpio_claim_output(chip, EN_PIN, 1)

    try:
        lgpio.gpio_write(chip, EN_PIN, 0) # Enable
        time.sleep(0.5)
        print("Moving... Watch the output shaft VERY closely (put a piece of tape on it!)")
        
        while True:
            lgpio.gpio_write(chip, STEP_PIN, 1)
            time.sleep(STEP_DELAY)
            lgpio.gpio_write(chip, STEP_PIN, 0)
            time.sleep(STEP_DELAY)
    except KeyboardInterrupt:
        pass
    finally:
        lgpio.gpio_write(chip, EN_PIN, 1)
        lgpio.gpiochip_close(chip)

run_test()