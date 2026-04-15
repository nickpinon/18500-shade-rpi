# LSM6DSOX Register Definitions
WHO_AM_I      = 0x0F
CTRL1_XL      = 0x10  # Accel config
CTRL2_G       = 0x11  # Gyro config
CTRL3_C       = 0x12  # Software reset and control
INT1_CTRL     = 0x0D  # Interrupt control

# Data Output Registers
OUTX_L_G      = 0x22  # Gyroscope starts here
OUTX_L_A      = 0x28  # Accelerometer starts here

# Expected Responses
WHO_AM_I_RSP  = 0x6C