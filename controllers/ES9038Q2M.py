import pickle
import math
from smbus2 import SMBus
from datetime import datetime
from .layout import Bin, I2CMapper
from time import sleep

class DAC_9038Q2M_Control(I2CMapper):
    def __init__(self, i2cAddr):
        super().__init__()
        FSR = 128
        MCLK = 1
        FCLK = 2  # CP_CLK_SEL

        self.i2cAddr = i2cAddr
        self.registers = [
            self.register(0, name="System Registers")
            .addMnemonic(
                self.registerRange(0, 0, registerID=0),
                self.mnemonicMapper(
                    "soft_reset",
                    {
                        "normal operation": Bin(int("0", 2),registerLen=1),
                        "reset to power-on defaults": Bin(int("1", 2), registerLen=1),
                    },
                    description="Software configurable hardware reset with \
                                 the ability to reset the design to its initial power-on configuration.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 3, registerID=0),
                self.mnemonicMapper(
                    "clk_gear",
                    {
                        "XI": Bin(int("00", 2), registerLen=2),
                        "XI / 2": Bin(int("01", 2), registerLen=2),
                        "XI / 4": Bin(int("10", 2), registerLen=2),
                        "XI / 8": Bin(int("11", 2), registerLen=2),
                    },
                    description="Configures a clock divider network that can reduce \
                                             the power consumption of the chip by reducing the clock \
                                             frequency supplied to both the digital core and analog stages.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 7, registerID=0),
                self.mnemonicMapper(
                    "osc_drv",
                    {
                        "full bias": Bin(int("0000", 2), registerLen=4),
                        "3/4 bias": Bin(int("1000", 2), registerLen=4),
                        "1/2 bias": Bin(int("1100", 2), registerLen=4),
                        "1/4 bias": Bin(int("1110", 2), registerLen=4),
                        "shutdown oscillator": Bin(int("1111", 2), registerLen=4),
                    },
                    description="Oscillator drive specifies the bias current to the oscillator pad.",
                ),
            ),
            self.register(1, name="Input selection")
            .addMnemonic(
                self.registerRange(0, 1, registerID=1),
                self.mnemonicMapper(
                    "input_select",
                    {
                        "serial": Bin(int("00", 2), registerLen=2),
                        "SPDIF": Bin(int("01", 2), registerLen=2),
                        "Reserved": Bin(int("10", 2), registerLen=2),
                        "DSD": Bin(int("11", 2), registerLen=2),
                    },
                    description="Configures the Sabre to use a particular input decoder if auto_select is disabled.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 3, registerID=1),
                self.mnemonicMapper(
                    "auto_select",
                    {
                        "disable auto-select": Bin(int("00", 2), registerLen=2),
                        "DSD or Serial": Bin(int("01", 2), registerLen=2),
                        "SPDIF or Serial": Bin(int("10", 2), registerLen=2),
                        "DSD, SPDIF or Serial": Bin(int("11", 2), registerLen=2),
                    },
                    description="Allows the Sabre to automatically select between either serial (I2S) or DSD input formats.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 5, registerID=1),
                self.mnemonicMapper(
                    "serial_mode",
                    {
                        "I2S Mode": Bin(int("00", 2), registerLen=2),
                        "left-justified mode": Bin(int("01", 2), registerLen=2),
                        "right-justified mode": Bin(int("10", 2), registerLen=2),
                        "right-justified mode2": Bin(int("11", 2), registerLen=2),
                    },
                    description="Configures the type of serial data.",
                ),
            )
            .addMnemonic(
                self.registerRange(6, 7, registerID=1),
                self.mnemonicMapper(
                    "serial_length",
                    {
                        "16 bits": Bin(int("00", 2), registerLen=2),
                        "24 bits": Bin(int("01", 2), registerLen=2),
                        "32 bits": Bin(int("10", 2), registerLen=2),
                        "32 bits2": Bin(int("11", 2), registerLen=2),
                    },
                    description="Selects how many DATA_CLK pulses exist per data word.",
                ),
            ),
            self.register(2, name="Mixing, Serial Data and Automute Configuration")
            .addMnemonic(
                self.registerRange(0, 1, registerID=2),
                self.mnemonicMapper(
                    "ch1_mix_sel",
                    {
                        "ch1": Bin(int("00", 2), registerLen=2),
                        "ch2": Bin(int("01", 2), registerLen=2),
                        "Reserved": Bin(int("10", 2), registerLen=2),
                        "Reserved": Bin(int("11", 2), registerLen=2),
                    },
                    description="Selects which data is mapped to DAC 1.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 3, registerID=2),
                self.mnemonicMapper(
                    "ch2_mix_sel",
                    {
                        "ch1": Bin(int("00", 2), registerLen=2),
                        "ch2": Bin(int("01", 2), registerLen=2),
                        "Reserved": Bin(int("10", 2), registerLen=2),
                        "Reservedl": Bin(int("11", 2), registerLen=2),
                    },
                    description="Selects which data is mapped to DAC 2.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 5, registerID=2),
                self.mnemonicMapper(
                    "reserved",
                    {
                        "Reserved": Bin(int("00", 2), registerLen=2),
                        "Reserved": Bin(int("01", 2), registerLen=2),
                        "Reserved": Bin(int("10", 2), registerLen=2),
                        "Reserved": Bin(int("11", 2), registerLen=2),
                    },
                    description="Reserved",
                ),
            )
            .addMnemonic(
                self.registerRange(6, 7, registerID=2),
                self.mnemonicMapper(
                    "automute",
                    {
                        "normal operation": Bin(int("00", 2), registerLen=2),
                        "perform mute": Bin(int("01", 2), registerLen=2),
                        "ramp2ground": Bin(int("10", 2), registerLen=2),
                        "perform mute/ramp2ground": Bin(int("11", 2), registerLen=2),
                    },
                    description="Configures the automute state machine, which allows the Sabre 2M to perform different power saving and sound optimizations.",
                ),
            ),
            self.register(3, name="SPDIF Configuration")
            .addMnemonic(
                self.registerRange(0, 0, registerID=3),
                self.mnemonicMapper(
                    "reserved",
                    {
                        "Reserved": Bin(int("0", 2), registerLen=1),
                        "Reserved": Bin(int("1", 2), registerLen=1),
                    },
                    description="Reserved",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 1, registerID=3),
                self.mnemonicMapper(
                    "spdif_ig_valid",
                    {
                        "ignore validflag": Bin(int("1", 2), registerLen=1),
                        "mute on invalid": Bin(int("0", 2), registerLen=1),
                    },
                    description="Configures the SPDIF decoder to ignore the ‘valid’ flag in the SPDIF stream.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 2, registerID=3),
                self.mnemonicMapper(
                    "spdif_ig_data",
                    {
                        "ignore dataflage": Bin(int("1", 2), registerLen=1),
                        "mute on dataflag": Bin(int("0", 2), registerLen=1),
                    },
                    description="Configures the SPDIF decoder to ignore the ‘data’ flag in the channel status bits.",
                ),
            )
            .addMnemonic(
                self.registerRange(3, 3, registerID=3),
                self.mnemonicMapper(
                    "spdif_user_bits",
                    {
                        "SPDIF user bits": Bin(int("1", 2), registerLen=1),
                        "SPDIF channel status bits": Bin(int("0", 2), registerLen=1),
                    },
                    description="Both SPDIF channel status bits and SPDIF user bits are available for readback via \
                                             the I2C interface. To reduce register count the channel status bits and user bits \
                                             occupy the same register space. Setting user_bits will present the SPDIF user bits \
                                             on the read-only register interface instead of the default channel status bits.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 7, registerID=3),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=4)}, description="Reserved"),
            ),
            self.register(4, name="Automute Time").addMnemonic(
                self.registerRange(0, 7, registerID=4),
                self.mnemonicFN(
                    "automute_time",
                    {
                        "in": (
                            lambda value: Bin(int(2096896 / value * FSR), registerLen=8)
                            if value != 0
                            else Bin(0, registerLen=8)
                        ),
                        "out": (
                            lambda value: 2096896 / (int(value) * FSR)
                            if value != Bin(0)
                            else 0
                        ),
                    },
                    description="Configures the amount of time the audio data \
                                             must remain below the automute_level before an \
                                             automute condition is flagged. Defaults to 0 \
                                             which disables automute. \
                                             Time in seconds = 2096896/(automute_time*FSR)",
                ),
            ),
            self.register(5, name="Automute Level")
            .addMnemonic(
                self.registerRange(0, 6, registerID=5),
                self.mnemonicFN(
                    "automute_level",
                    {
                        "in": lambda value: Bin(int(-value), registerLen=7),
                        "out": lambda value: -int(value),
                    },
                    description="Configures the threshold which the audio must be \
                                             below before an automute condition is flagged. \
                                             The level is measured in decibels (dB) and defaults \
                                             to -104dB. Note: This register works in tandem with \
                                             automute_time to create the automute condition",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=5),
                self.mnemonicMapper(
                    "reserved",
                    {
                        "Reserved": Bin(int("0", 2), registerLen=1),
                        "Reserved": Bin(int("1", 2), registerLen=1),
                    },
                    description="Reserved",
                ),
            ),
            self.register(6, name="De-emphasis, DoP and Volume Ramp Rate")
            .addMnemonic(
                self.registerRange(0, 2, registerID=6),
                self.mnemonicFN(
                    "volume_rate",
                    {
                        "in": (
                            lambda value: Bin(int(math.log(value * 512 / FSR, 2.0) if value != 0 else 0), registerLen=3)
                        ),
                        "out": (lambda value: (2 ** int(value) * FSR) / 512),
                    },
                    description="Selects a volume ramp rate to use when transitioning between \
                                             different volume levels. The volume ramp rate is measured in  \
                                             decibels per second (dB/s).",
                ),
            )
            .addMnemonic(
                self.registerRange(3, 3, registerID=6),
                self.mnemonicMapper(
                    "dop_enable",
                    {
                        "enabled": Bin(int("1", 2), registerLen=1),
                        "disabled": Bin(int("0", 2), registerLen=1),
                    },
                    description="Selects whether the DSD over PCM (DoP) logic is enabled.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 5, registerID=6),
                self.mnemonicMapper(
                    "deemph_sel",
                    {
                        "Reserved": Bin(int("11", 2), registerLen=2),
                        "48kHz": Bin(int("10", 2), registerLen=2),
                        "44.1kHz": Bin(int("01", 2), registerLen=2),
                        "32kHz": Bin(int("00", 2), registerLen=2),
                    },
                    description="Selects which de-emphasis filter is used.",
                ),
            )
            .addMnemonic(
                self.registerRange(6, 6, registerID=6),
                self.mnemonicMapper(
                    "deemph_bypass",
                    {
                        "disable": Bin(int("1", 2), registerLen=1),
                        "enable": Bin(int("0", 2), registerLen=1),
                    },
                    description="Enables or disables the built-in de-emphasis filters.",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=6),
                self.mnemonicMapper(
                    "auto_deemph",
                    {
                        "disable": Bin(int("1", 2), registerLen=1),
                        "enable": Bin(int("0", 2), registerLen=1),
                    },
                    description="Automatically engages the de-emphasis filters when SPDIF \
                                             data is provides and the SPDIF channel status bits contains\
                                             valid de-emphasis settings.",
                ),
            ),
            self.register(7, name="Filter Bandwidth and System Mute")
            .addMnemonic(
                self.registerRange(0, 0, registerID=7),
                self.mnemonicMapper(
                    "mute",
                    {
                        "mute both channels": Bin(int("1", 2), registerLen=1),
                        "normal operation": Bin(int("0", 2), registerLen=1),
                    },
                    description="Mutes all 2 channels of the Sabre DAC.",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 2, registerID=7),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=2)}, description="Reserved."),
            )
            .addMnemonic(
                self.registerRange(3, 3, registerID=7),
                self.mnemonicMapper(
                    "bypass_osf",
                    {
                        "built-in oversampling": Bin(int("0", 2), registerLen=1),
                        "external oversampling": Bin(int("1", 2), registerLen=1),
                    },
                    description="Allows the use of an external 8x upsampling filter, bypassing the internal interpolating FIR filter.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 4, registerID=7),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved."),
            )
            .addMnemonic(
                self.registerRange(5, 7, registerID=7),
                self.mnemonicMapper(
                    "filter_shape",
                    {
                        "brick_wall": Bin(int("111", 2), registerLen=3),
                        "corrected minimum phase fast roll-off": Bin(int("110", 2), registerLen=3),
                        "Reserved": Bin(int("101", 2), registerLen=3),
                        "apodizing fast roll-off filter": Bin(int("100", 2), registerLen=3),
                        "minimum phase slow roll-off filter": Bin(int("011", 2), registerLen=3),
                        "minimum phase fast roll-off filter": Bin(int("010", 2), registerLen=3),
                        "linear phase slow roll-off filter": Bin(int("001", 2), registerLen=3),
                        "linear phase fast roll-off filter": Bin(int("000", 2), registerLen=3),
                    },
                    description="Selects the type of filter to use during the 8x FIR interpolation phase.",
                ),
            ),
            self.register(8, name="GPIO1-2 Configuration")
            .addMnemonic(
                self.registerRange(0, 3, registerID=8),
                self.mnemonicMapper(
                    "gpio1_cfg",
                    {
                        "Automute Status": Bin(0, registerLen=4),
                        "Lock Status": Bin(1, registerLen=4),
                        "Volume Min": Bin(2, registerLen=4),
                        "CLK": Bin(3, registerLen=4),
                        "Automute/Lock Interrupt": Bin(4, registerLen=4),
                        "ADC_CLK": Bin(5, registerLen=4),
                        "Reserved": Bin(6, registerLen=4),
                        "Output 1'b0": Bin(7, registerLen=4),
                        "Standard Input": Bin(8, registerLen=4),
                        "Input Select": Bin(9, registerLen=4),
                        "Mute All": Bin(10, registerLen=4),
                        "Reserved": Bin(11, registerLen=4),
                        "Reserved": Bin(12, registerLen=4),
                        "Reserved": Bin(13, registerLen=4),
                        "Soft Start Complete": Bin(14, registerLen=4),
                        "Output 1'b1": Bin(15, registerLen=4),
                    },
                    description="The GPIO can each be configured in one of several ways. \n\
                                             The table below is for programming each independent GPIO configuration value.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 7, registerID=8),
                self.mnemonicMapper(
                    "gpio2_cfg",
                    {
                        "Automute Status": Bin(0, registerLen=4),
                        "Lock Status": Bin(1, registerLen=4),
                        "Volume Min": Bin(2, registerLen=4),
                        "CLK": Bin(3, registerLen=4),
                        "Automute/Lock Interrupt": Bin(4, registerLen=4),
                        "ADC_CLK": Bin(5, registerLen=4),
                        "Reserved": Bin(6, registerLen=4),
                        "Output 1'b0": Bin(7, registerLen=4),
                        "Standard Input": Bin(8, registerLen=4),
                        "Input Select": Bin(9, registerLen=4),
                        "Mute All": Bin(10, registerLen=4),
                        "Reserved": Bin(11, registerLen=4),
                        "Reserved": Bin(12, registerLen=4),
                        "ADC.Input": Bin(13, registerLen=4),
                        "Soft Start Complete": Bin(14, registerLen=4),
                        "Output 1'b1": Bin(15, registerLen=4),
                    },
                    description="The GPIO can each be configured in one of several ways. \n\
                                             The table below is for programming each independent GPIO configuration value.",
                ),
            ),
            self.register(9, name="Reserved 9")
            .addMnemonic(
                self.registerRange(0, 3, registerID=9),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=4)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(4, 7, registerID=9),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=4)}, description="Reserved"),
            ),
            self.register(10, name="Master Mode and Sync Configuration")
            .addMnemonic(
                self.registerRange(0, 3, registerID=10),
                self.mnemonicMapper(
                    "lock_speed",
                    {
                        "16384 FSL": Bin(0, registerLen=4),
                        "8192 FSL": Bin(1, registerLen=4),
                        "5461 FSL": Bin(2, registerLen=4),
                        "4096 FSL": Bin(3, registerLen=4),
                        "3276 FSL": Bin(4, registerLen=4),
                        "2730 FSL": Bin(5, registerLen=4),
                        "2340 FSL": Bin(6, registerLen=4),
                        "2048 FSL": Bin(7, registerLen=4),
                        "1820 FSL": Bin(8, registerLen=4),
                        "1638 FSL": Bin(9, registerLen=4),
                        "1489 FSL": Bin(10, registerLen=4),
                        "1365 FSL": Bin(11, registerLen=4),
                        "1260 FSL": Bin(12, registerLen=4),
                        "1170 FSL": Bin(13, registerLen=4),
                        "1092 FSL": Bin(14, registerLen=4),
                        "1024 FSL": Bin(15, registerLen=4),
                    },
                    description="Sets the number of audio samples required before the DPLL \
                                             and ASRC lock to the incoming signal. More audio samples \
                                             gives a better initial estimate of the MCLK/FSR ratio at the \
                                             expense of a longer locking interval.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 4, registerID=10),
                self.mnemonicMapper(
                    "128fs_mode (128*FSR mode)",
                    {
                        "enables MCLK": Bin(int("1", 2), registerLen=1),
                        "disables MCLK": Bin(int("0", 2), registerLen=1),
                    },
                    description="Enables operation of the DAC while in synchronous mode with a \
                                             128*FSR MCLK in PCM normal or OSF bypass mode only.",
                ),
            )
            .addMnemonic(
                self.registerRange(5, 6, registerID=10),
                self.mnemonicMapper(
                    "master_div",
                    {
                        "MCLK/2": Bin(int("00", 2), registerLen=2),
                        "MCLK/4": Bin(int("01", 2), registerLen=2),
                        "MCLK/8": Bin(int("10", 2), registerLen=2),
                        "MCLK/16": Bin(int("11", 2), registerLen=2),
                    },
                    description="Sets the frame clock (DATA1) and DATA_CLK frequencies when in \
                                             master mode. This register is used when in normal synchronous operation. DATA_CLK frequency = ***",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=10),
                self.mnemonicMapper(
                    "master_mode",
                    {
                        "disable": Bin(int("0", 2), registerLen=1),
                        "enable": Bin(int("1", 2), registerLen=1),
                    },
                    description="Enables master mode which causes the Sabre to drive the DATA_CLK and DATA1 signals when \
                                                in I2S mode. Can also be enabled when in DSD mode to enable DATA_CLK only.",
                ),
            ),
            self.register(11, name="SPDIF Select")
            .addMnemonic(
                self.registerRange(0, 3, registerID=11),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=4)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(4, 7, registerID=11),
                self.mnemonicMapper(
                    "spdif_sel",
                    {
                        "DATA_CLK": Bin(0, registerLen=4),
                        "DATA1": Bin(1, registerLen=4),
                        "DATA2": Bin(2, registerLen=4),
                        "GPIO1": Bin(3, registerLen=4),
                        "GPIO2": Bin(4, registerLen=4),
                    },
                    description="Selects which input to use when decoding SPDIF data. Note: If using a \
                                                GPIO the GPIO configuration must be set to an input.",
                ),
            ),
            self.register(12, name="ASRC/DPLL Bandwidth")
            .addMnemonic(
                self.registerRange(0, 3, registerID=12),
                self.mnemonicMapper(
                    "dpll_bw_dsd",
                    {
                        "DPLL Off": Bin(0, registerLen=4),
                        "Lowerst Bandwidth": Bin(1, registerLen=4),
                        "Bandwith Mode 2": Bin(2, registerLen=4),
                        "Bandwith Mode 3": Bin(3, registerLen=4),
                        "Bandwith Mode 4": Bin(4, registerLen=4),
                        "Bandwith Mode 5": Bin(5, registerLen=4),
                        "Bandwith Mode 6": Bin(6, registerLen=4),
                        "Bandwith Mode 7": Bin(7, registerLen=4),
                        "Bandwith Mode 8": Bin(8, registerLen=4),
                        "Bandwith Mode 9": Bin(9, registerLen=4),
                        "Bandwith Mode 10": Bin(10, registerLen=4),
                        "Bandwith Mode 11": Bin(11, registerLen=4),
                        "Bandwith Mode 12": Bin(12, registerLen=4),
                        "Bandwith Mode 13": Bin(13, registerLen=4),
                        "Bandwith Mode 14": Bin(14, registerLen=4),
                        "Highest Bandwidth": Bin(15, registerLen=4),
                    },
                    description="Sets the bandwidth of the DPLL when operating in DSD mode.",
                )
            )
            .addMnemonic(
                self.registerRange(4, 7, registerID=12),
                self.mnemonicMapper(
                    "dpll_bw_serial",
                    {
                        "DPLL Off": Bin(0, registerLen=4),
                        "Lowerst Bandwidth": Bin(1, registerLen=4),
                        "Bandwith Mode 2": Bin(2, registerLen=4),
                        "Bandwith Mode 3": Bin(3, registerLen=4),
                        "Bandwith Mode 4": Bin(4, registerLen=4),
                        "Bandwith Mode 5": Bin(5, registerLen=4),
                        "Bandwith Mode 6": Bin(6, registerLen=4),
                        "Bandwith Mode 7": Bin(7, registerLen=4),
                        "Bandwith Mode 8": Bin(8, registerLen=4),
                        "Bandwith Mode 9": Bin(9, registerLen=4),
                        "Bandwith Mode 10": Bin(10, registerLen=4),
                        "Bandwith Mode 11": Bin(11, registerLen=4),
                        "Bandwith Mode 12": Bin(12, registerLen=4),
                        "Bandwith Mode 13": Bin(13, registerLen=4),
                        "Bandwith Mode 14": Bin(14, registerLen=4),
                        "Highest Bandwidth": Bin(15, registerLen=4),
                    },
                    description="Sets the bandwidth of the DPLL when operating in I2S mode.",
                ),
            ),
            self.register(13, name="THD Bypass")
            .addMnemonic(
                self.registerRange(0, 5, registerID=13),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=6)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(6, 6, registerID=13),
                self.mnemonicMapper(
                    "thd_enb",
                    {
                        "enable THD": Bin(1, registerLen=1),
                        "disable THD": Bin(0, registerLen=1),
                    },
                    description="Selects whether to disable the THD compensation logic. THD \
                                              compensation is enabled by default and can be configured to correct \
                                              for second and third harmonic distortion.",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=13),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved"),
            ),
            self.register(14, name="Soft Start Configuration")
            .addMnemonic(
                self.registerRange(0, 4, registerID=14),
                self.mnemonicFN(
                    "soft start time",
                    {
                        "in": lambda x: Bin(int(math.log2(x * MCLK / 4096) - 1 if x != 0 else 0), registerLen=5),
                        "out": lambda x: 4096 * (2 ** (int(x) + 1)) / MCLK,
                    },
                    description="Sets the amount of time that it takes to perform a \
                                              soft start ramp. Thitime affects both ramp to ground \
                                              and ramp to AVCC/2. This value is valid from 0 to 20 (inclusive).",
                ),
            )
            .addMnemonic(
                self.registerRange(5, 5, registerID=14),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(6, 6, registerID=14),
                self.mnemonicMapper(
                    "soft_start_on_lock",
                    {
                        "Always soft start": Bin(0, registerLen=1),
                        "Soft start when locked": Bin(1, registerLen=1),
                    },
                    description="Reserved",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=14),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved"),
            ),
            self.register((15, 16), name="Volume Control")
            .addMnemonic(
                self.registerMultiRange(0, 7, registerID=15),
                self.mnemonicFN(
                    "volume1",
                    {"in": lambda x: Bin(-int(x) * 2, registerLen=8), "out": lambda x: -int(x) * 0.5},
                    description="Default of 8’d80 (-40dB) \
                                              -0dB to -127.5dB with 0.5dB steps",
                ),
            )
            .addMnemonic(
                self.registerMultiRange(0, 7, registerID=16),
                self.mnemonicFN(
                    "volume2",
                    {"in": lambda x: Bin(-int(x) * 2, registerLen=8), "out": lambda x: -int(x) * 0.5},
                    description="Default of 8’d80 (-40dB) \
                                              -0dB to -127.5dB with 0.5dB steps",
                ),
            ),
            self.register((17, 18, 19, 20), name="Master Trim").addMnemonic(
                self.registerMultiRange(0, 31, registerID="all"),
                self.mnemonicFN(
                    "master_trim",
                    {"in": lambda x: Bin(int(-x * 2), registerLen=4*8), "out": lambda x: -int(x) * 0.5},
                    description="A 32 bit signed value that sets the 0dB level for all volume controls. \
                                              Defaults to full-scale (32’h7FFFFFFF).",
                ),
            ),
            self.register(21, name="GPIO Input Selection")
            .addMnemonic(
                self.registerRange(0, 3, registerID=21),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=4)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(4, 5, registerID=21),
                self.mnemonicMapper(
                    "gpio_sel1",
                    {
                        "serial data (I2S/LJ)": Bin(0, registerLen=2),
                        "SPDIF": Bin(1, registerLen=2),
                        "Reserved": Bin(2, registerLen=2),
                        "DSD data": Bin(3, registerLen=2),
                    },
                    description="Selects which input type will be selected when GPIO1 = Input Select",
                ),
            )
            .addMnemonic(
                self.registerRange(6, 7, registerID=21),
                self.mnemonicMapper(
                    "gpio_sel2",
                    {
                        "serial data (I2S/LJ)": Bin(0, registerLen=2),
                        "SPDIF": Bin(1, registerLen=2),
                        "Reserved": Bin(2, registerLen=2),
                        "DSD data": Bin(3, registerLen=2),
                    },
                    description="Selects which input type will be selected when GPIO2 = Input Select",
                ),
            ),
            self.register((22, 23), name="THD Compensation C2").addMnemonic(
                self.registerMultiRange(0, 15, registerID="all"),
                self.mnemonicFN(
                    "thd_comp_c2",
                    {"in": lambda x: Bin(int(x), registerLen=16), "out": lambda x: int(x)},
                    description="A 16-bit signed coefficient for correcting for the \
                                              second harmonic distortion. Defaults to 16’d0.",
                ),
            ),
            self.register((24, 25), name="THD Compensation C3").addMnemonic(
                self.registerMultiRange(0, 15, registerID="all"),
                self.mnemonicFN(
                    "thd_comp_c3",
                    {"in": lambda x: Bin(int(x), registerLen=16), "out": lambda x: int(x)},
                    description="A 16-bit signed coefficient for correcting for the \
                                              third harmonic distortion. Defaults to 16’d0.",
                ),
            ),
            self.register(26, name="Reserved 26").addMnemonic(
                self.registerRange(0, 7, registerID=26),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=8)}, description="Reserved"),
            ),
            self.register(27, name="General Configuration")
            .addMnemonic(
                self.registerRange(0, 1, registerID=27),
                self.mnemonicMapper(
                    "18db_gain",
                    {
                        "No gain on either channels": Bin(int("00", 2), registerLen=2),
                        "Normal gain on channel 2, +18dB gain on channel 1": Bin(
                            int("01", 2), registerLen=2
                        ),
                        "+18dB gain on channel 2, normal gain on channel 1": Bin(
                            int("10", 2), registerLen=2
                        ),
                        "+18dB gain on both channel 2 and channel 1": Bin(int("11", 2), registerLen=2),
                    },
                    description="Applies +18dB gain to a the DAC datapath.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 2, registerID=27),
                self.mnemonicMapper(
                    "latch_volume",
                    {
                        "Disables updates": Bin(0, registerLen=1),
                        "Syncronize to volume registers": Bin(1, registerLen=1),
                    },
                    description="Keeps the volume coefficients in synchronization with the programmed volume register.",
                ),
            )
            .addMnemonic(
                self.registerRange(3, 3, registerID=27),
                self.mnemonicMapper(
                    "ch1_volume",
                    {
                        "Allow independent control": Bin(0, registerLen=1),
                        "Use the ch1 volume for ch1/2": Bin(1, registerLen=1),
                    },
                    description="Allows channel 2 to share the channel 1 volume control. \
                                              This allows forperfectly syncing up the two channel gains.",
                ),
            )
            .addMnemonic(
                self.registerRange(4, 4, registerID=27),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(5, 6, registerID=27),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=2)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=27),
                self.mnemonicMapper(
                    "asrc_en",
                    {
                        "Disabled": Bin(0, registerLen=1),
                        "Enabled": Bin(1, registerLen=1),
                    },
                    description="Selects whether the ASRC is enabled.",
                ),
            ),
            self.register(28, name="Reserved 28").addMnemonic(
                self.registerRange(0, 7, registerID=28),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=8)}, description="Reserved"),
            ),
            self.register(29, name="GPIO Configuration")
            .addMnemonic(
                self.registerRange(0, 5, registerID=29),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=6)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(6, 7, registerID=29),
                self.mnemonicMapper(
                    "invert_gpio",
                    {
                        "Normal": Bin(int("00", 2), registerLen=2),
                        "Invert GPIO1": Bin(int("01", 2), registerLen=2),
                        "Invert GPIO2": Bin(int("10", 2), registerLen=2),
                        "Invert GPIO1/2": Bin(int("11", 2), registerLen=2),
                    },
                    description="Allows each GPIO output to be inverted independently.",
                ),
            ),
            self.register((30, 31), name="Charge Pump Clock")
            .addMnemonic(
                self.registerMultiRange(0, 11, registerID="all"),
                self.mnemonicFN(
                    "cp_clk_div",
                    {
                        "in": lambda x: Bin(int(FCLK / (x * 2) if x != 0 else 0), registerLen=12),
                        "out": lambda x: FCLK / (int(x) * 2) if x != Bin(0) else 0,
                    },
                    description="Sets the divider ratio for the change pump clock. fclk is the frequency of the clock selected by cp_clk sel.",
                ),
            )
            .addMnemonic(
                self.registerMultiRange(12, 13, registerID="all"),
                self.mnemonicMapper(
                    "cp_clk_en",
                    {
                        "Tristate output": Bin(int("00", 2), registerLen=2),
                        "Tied to GND": Bin(int("01", 2), registerLen=2),
                        "Tied to DVDD": Bin(int("10", 2), registerLen=2),
                        "Active": Bin(int("11", 2), registerLen=2),
                    },
                    description="Sets the state of the charge pump clock.",
                ),
            )
            .addMnemonic(
                self.registerMultiRange(14, 15, registerID="all"),
                self.mnemonicMapper(
                    "cp_clk_sel",
                    {
                        "f_CLK=XI": Bin(int("00", 2), registerLen=2),
                        "Reserved": Bin(int("01", 2), registerLen=2),
                        "Reserved": Bin(int("10", 2), registerLen=2),
                        "Reserved": Bin(int("11", 2), registerLen=2),
                    },
                    description="Selects which clock will be used as the reference clock (fCLK ) for the charge pump clock.",
                ),
            ),
            self.register(32, name="Reserved 32").addMnemonic(
                self.registerRange(0, 7, registerID=32),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=8)}, description="Reserved"),
            ),
            self.register(33, name="Interrupt Mask")
            .addMnemonic(
                self.registerRange(0, 0, registerID=33),
                self.mnemonicMapper(
                    "lock_mask",
                    {"0_mask": Bin(0, registerLen=1), "1_mask": Bin(1, registerLen=1)},
                    description="Masks the lock status bit from flagging an interrupt.",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 1, registerID=33),
                self.mnemonicMapper(
                    "automute_mask",
                    {"0_mask": Bin(0, registerLen=1), "1_mask": Bin(1, registerLen=1)},
                    description="Masks the automute bit from flagging an interrupt.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 5, registerID=33),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=4)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(6, 7, registerID=33),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=2)}, description="Reserved"),
            ),
            self.register((34, 35, 36, 37), name="Programmable NCO").addMnemonic(
                self.registerMultiRange(0, 31, registerID="all"),
                self.mnemonicFN(
                    "nco_num",
                    {
                        "in": lambda x: Bin(int(x * 2 ** 32 / MCLK), registerLen=32),
                        "out": lambda x: (int(x) * MCLK) / 2 ** 32,
                    },
                    description="An unsigned 32-bit quantity that provides the ratio between MCLK and \
                                             DATA_CLK. This value can be used to generate arbitrary DATA_CLK \
                                             frequencies in master mode. A value of 0 disables this operating mode. \
                                             Note: Master mode must still be enabled for the Sabre to drive the \
                                             DATA_CLK and DATA1 pins. You must also select either serial mode or \
                                             DSD mode in the input_select register to determine whether DATA_CLK \
                                             should be driven alone (DSD mode) or both DATA_CLK and DATA1 \
                                             32’d0: disables NCO mode (default)\
                                             32’d?: enables NCO mode",
                ),
            ),
            self.register(38, name="Reserved 38").addMnemonic(
                self.registerRange(0, 7, registerID=38),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=8)}, description="Reserved"),
            ),
            self.register(39, name="General Configuration 2")
            .addMnemonic(
                self.registerRange(0, 1, registerID=39),
                self.mnemonicMapper(
                    "sw_ctrl_en",
                    {
                        "Switch external controlled": Bin(int("00", 2), registerLen=2),
                        "Switch control is set to 0": Bin(int("01", 2), registerLen=2),
                        "Reserved": Bin(int("10", 2), registerLen=2),
                        "Switch control is set to 1": Bin(int("11", 2), registerLen=2),
                    },
                    description="Selects the operating mode of the external switch control.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 5, registerID=39),
                self.mnemonicMapper("reserved", {"Reserved":Bin(0, registerLen=4)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(6, 6, registerID=39),
                self.mnemonicMapper(
                    "amp_pdb",
                    {
                        "Disabled": Bin(int("0", 2), registerLen=1),
                        "Enabled": Bin(int("1", 2), registerLen=1),
                    },
                    description="Enables of disables the headphone amplifier.",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=39),
                self.mnemonicMapper(
                    "amp_pdb_ss",
                    {
                        "Amplifier controlled by amp_pdb": Bin(int("0", 2), registerLen=1),
                        "Shut amp down when DAC to ground": Bin(int("1", 2), registerLen=1),
                    },
                    description="Powers the amplifier stage down when the digital core ramps to ground. \
                                  This is useful when powering down the amplifier when in automute mode.",
                ),
            ),
            self.register(40, name="Programmable FIR RAM Address")
            .addMnemonic(
                self.registerRange(0, 6, registerID=40),
                self.mnemonicFN(
                    "coeff_addr",
                    {"in": lambda x: Bin(int(x), registerLen=7), "out": lambda x: int(x)},
                    description="Selects the coefficient address when writing custom coefficients for the oversampling filter.",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=40),
                self.mnemonicMapper(
                    "coeff_stage",
                    {
                        "stage 1": Bin(0, registerLen=1),
                        "stage 2": Bin(1, registerLen=1),
                    },
                    description="Selects which stage of the filter to write.",
                ),
            ),
            self.register((41, 42, 43), name="Programmable FIR RAM Data").addMnemonic(
                self.registerMultiRange(0, 23, registerID="all"),
                self.mnemonicFN(
                    "prog_coeff_data",
                    {"in": lambda x: Bin(int(x), registerLen=24, mode="signed"), "out": lambda x: int(x)},
                    description="A 24bit signed filter coefficient that will be \
                                 written to the address defined in prog_coeff_addr.",
                ),
            ),
            self.register(44, name="Programmable FIR Configuration")
            .addMnemonic(
                self.registerRange(0, 0, registerID=44),
                self.mnemonicMapper(
                    "prog_en",
                    {
                        "Built-in filter selected by filter_shape": Bin(0, registerLen=1),
                        "Coefficients programmed via prog_coeff_data": Bin(1, registerLen=1),
                    },
                    description="Enables the custom oversampling filter coefficients.",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 1, registerID=44),
                self.mnemonicMapper(
                    "prog_we",
                    {
                        "Disables write signal to the coefficient RAM": Bin(0, registerLen=1),
                        "Enables write signal to the coefficient RAM": Bin(1, registerLen=1),
                    },
                    description="Enables writing to the programmable coefficient RAM.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 2, registerID=44),
                self.mnemonicMapper(
                    "stage2_even",
                    {
                        "Sine symmetric filter (27 coeff.)": Bin(0, registerLen=1),
                        "Cosine symmetric filter (28 coeff.)": Bin(1, registerLen=1),
                    },
                    description="Selects the symmetry of the stage 2 oversampling filter.",
                ),
            )
            .addMnemonic(
                self.registerRange(3, 7, registerID=44),
                self.mnemonicMapper(
                    "reserved", {"Reserved": Bin(0, registerLen=5)}, description="Not connected in the digital core."
                ),
            ),
            self.register(45, name="Low Power and Auto Calibration")
            .addMnemonic(
                self.registerRange(0, 0, registerID=45),
                self.mnemonicMapper(
                    "bias_ctr",
                    {"Off": Bin(0, registerLen=1), "On": Bin(1, registerLen=1)},
                    description="Sets the state of the BIAS pin.",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 3, registerID=45),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=3)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(4, 4, registerID=45),
                self.mnemonicMapper(
                    "calib_latch",
                    {"No update": Bin(0, registerLen=1), "Continue routine update": Bin(1, registerLen=1)},
                    description="Continues updating the calibration routine while set to 1’b1.",
                ),
            )
            .addMnemonic(
                self.registerRange(5, 5, registerID=45),
                self.mnemonicMapper(
                    "calib_en",
                    {"Disable": Bin(0, registerLen=1), "Enable": Bin(1, registerLen=1)},
                    description="Enables master trim calibration via the ADC input.",
                ),
            )
            .addMnemonic(
                self.registerRange(6, 7, registerID=45),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=2)}, description="reserved"),
            ),
            self.register(46, name="ADC Configuration")
            .addMnemonic(
                self.registerRange(0, 0, registerID=46),
                self.mnemonicMapper(
                    "adc_pdb",
                    {"Shuts down ADC": Bin(0, registerLen=1), "Enables ADC": Bin(1, registerLen=1)},
                    description="Shuts down the ADC. Note: GPIO must be configured as ADC input for the ADC to function correctly.",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 1, registerID=46),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(2, 2, registerID=46),
                self.mnemonicMapper(
                    "adc_ditherb",
                    {"TPDF shaped dither": Bin(0, registerLen=1), "Disabled dither": Bin(1, registerLen=1)},
                    description="Allows the ADC dither to be disabled on a per ADC basis.",
                ),
            )
            .addMnemonic(
                self.registerRange(3, 3, registerID=46),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerRange(4, 5, registerID=46),
                self.mnemonicMapper(
                    "adc_clk",
                    {"CLK": Bin(0, registerLen=2), "CLK/2": Bin(1, registerLen=2), "CLK/4": Bin(2, registerLen=2), "CLK/8": Bin(3, registerLen=2)},
                    description="Sets the clock dividing ration for the ADC analog section.\
                                              This also affects the decimation filter stages. ADC_CLK  = *",
                ),
            )
            .addMnemonic(
                self.registerRange(6, 6, registerID=46),
                self.mnemonicMapper(
                    "adc_order",
                    {
                        "Uses first order modulation": Bin(0, registerLen=1),
                        "Uses second order modulation": Bin(1, registerLen=1),
                    },
                    description="Selects whether the ADC uses a first order modulator or a \
                                              second order modulator in the analog section.",
                ),
            )
            .addMnemonic(
                self.registerRange(7, 7, registerID=46),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=1)}, description="Reserved"),
            ),
            self.register((47, 48, 49, 50, 51, 52), name="ADC Filter Configuration")
            .addMnemonic(
                self.registerMultiRange(0, 15, registerID="all"),
                self.mnemonicFN(
                    "adc_ftr_scale",
                    {"in": lambda x: Bin(int(x), registerLen=16), "out": lambda x: int(x)},
                    description="The Sabre contains two decimation filters for filtering the ADC data. \
                                              These filters are configurable via the ADC filter configuration registers. \
                                              They are set as a low pass filter by default.",
                ),
            )
            .addMnemonic(
                self.registerMultiRange(16, 31, registerID="all"),
                self.mnemonicFN(
                    "adc_fbq_scale1",
                    {"in": lambda x: Bin(int(x), registerLen=16), "out": lambda x: int(x)},
                    description="The Sabre contains two decimation filters for filtering the ADC data. \
                                              These filters are configurable via the ADC filter configuration registers. \
                                              They are set as a low pass filter by default.",
                ),
            )
            .addMnemonic(
                self.registerMultiRange(32, 47, registerID="all"),
                self.mnemonicFN(
                    "adc_fbq_scale2",
                    {"in": lambda x: Bin(int(x), registerLen=16), "out": lambda x: int(x)},
                    description="The Sabre contains two decimation filters for filtering the ADC data. \
                                              These filters are configurable via the ADC filter configuration registers. \
                                              They are set as a low pass filter by default.",
                ),
            ),
            self.register((53, 54), name="Reserved 53/54")
            .addMnemonic(
                self.registerMultiRange(0, 11, registerID="all"),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=12)}, description="Reserved"),
            )
            .addMnemonic(
                self.registerMultiRange(12, 15, registerID="all"),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=4)}, description="Reserved"),
            ),
            self.register(64, name="Chip ID and Status", writeable=False)
            .addMnemonic(
                self.registerRange(0, 0, registerID=64),
                self.mnemonicMapper(
                    "lock_status",
                    {
                        "DPLL not locked": Bin(0, registerLen=1),
                        "DPLL locked": Bin(1, registerLen=1),
                    },
                    description="Indicator for when the DPLL is locked (when in slave mode) or 1’b1 \
                                              when the Sabre is the master.",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 1, registerID=64),
                self.mnemonicMapper(
                    "automute_status",
                    {
                        "Automute inactive": Bin(0, registerLen=1),
                        "Automute active": Bin(1, registerLen=1),
                    },
                    description="Indicator for when automute has become active.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 7, registerID=64),
                self.mnemonicFN(
                    "chip_id",
                    {"in": lambda x: Bin(int(x), registerLen=2*8), "out": lambda x: int(x)},
                    description="Determines the chip identification.",
                ),
            ),
            self.register(65, name="GPIO Readback", writeable=False)
            .addMnemonic(
                self.registerRange(0, 0, registerID=65),
                self.mnemonicFN(
                    "gpio1",
                    {
                        "in": lambda x: Bin(int(x), registerLen=1),
                        "out": lambda x: int(x),
                    },
                    description="Contains the state of the GPIO1 pin.",
                ),
            )
            .addMnemonic(
                self.registerRange(1, 1, registerID=65),
                self.mnemonicFN(
                    "gpio2",
                    {
                        "in": lambda x: Bin(int(x), registerLen=1),
                        "out": lambda x: int(x),
                    },
                    description="Contains the state of the GPIO2 pin.",
                ),
            )
            .addMnemonic(
                self.registerRange(2, 7, registerID=65),
                self.mnemonicMapper("reserved", {"Reserved": Bin(0, registerLen=6)}, description="Reserved."),
            ),
            self.register(
                (66, 67, 68, 69), name="DPLL Number", writeable=False
            ).addMnemonic(
                self.registerMultiRange(0, 31, registerID="all"),
                self.mnemonicFN(
                    "dpll_num",
                    {
                        "in": lambda x: Bin(int(x * 2 ** 32 / MCLK), registerLen=32),
                        "out": lambda x: int(x) * MCLK / 2 ** 32,
                    },
                    description="Contains the ratio between the MCLK and the audio clock rate once the \
                                              DPLL has acquired lock. This value is latched on reading the LSB, so \
                                              register 66 must be read first to acquire the latest DPLL value. The \
                                              value is latched on LSB because the DPLL number can be changing as \
                                              the I2C transactions are performed.",
                ),
            ),
            self.register(
                tuple(range(70, 94)),
                name="SPDIF Channel Status/User Status",
                writeable=False,
            ).addMnemonic(
                self.registerMultiRange(0, 191, registerID="all"),
                self.mnemonicFN(
                    "spdif_status",
                    {
                        "in": lambda x: Bin(int(x), registerLen=8*(94-70)),
                        "out": lambda x: int(x),
                    },
                    description="Contains either the SPDIF channel status (table shown below) or the \
                                              SPDIF user bits. This selection can be made via register 1 (spdif_load_user_bits).",
                ),
            ),
        ]
        self.updateRegisterNames()

    def i2c_init(self):
        with SMBus(bus=1, force=True) as bus:
            for register in self.registers:
                # Returned value is a list of 16 bytes
                register.fillData(
                    {
                        r: Bin(bus.read_byte_data(self.i2cAddr, r), registerLen=8, mode="unsigned")
                        for r in register.registers
                    }
                )
        for register in self.registers:
            print(str(register) + "\n")

    def fir_update(self, data, filter="fir1"):
        if filter == "fir1":
            assert(len(data) == 128)
            self.get("Programmable FIR Configuration").prog_we = "Enables write signal to the coefficient RAM"
            self.i2c_update()
            self.get("Programmable FIR RAM Address").coeff_stage = "stage one"
            self.i2c_update()
            for i, d in enumerate(data):
                self.get("Programmable FIR RAM Address").coeff_addr = i
                self.i2c_update()
                self.get("Programmable FIR RAM Data").prog_coeff_data = d
                self.i2c_update()

            self.get("Programmable FIR Configuration").prog_we = "Disables write signal to the coefficient RAM"
            self.i2c_update()
        elif filter == "fir2":
            assert(len(data) == 28 or len(data) == 14)
            self.get("Programmable FIR Configuration").prog_we = "Enables write signal to the coefficient RAM"
            self.i2c_update()
            self.get("Programmable FIR RAM Address").coeff_stage = "stage two"
            self.i2c_update()
            for i, d in enumerate(data[:14]):
                self.get("Programmable FIR RAM Address").coeff_addr = i
                self.i2c_update()
                self.get("Programmable FIR RAM Data").prog_coeff_data = d
                self.i2c_update()
            self.get("Programmable FIR Configuration").prog_we = "Disables write signal to the coefficient RAM"
            self.i2c_update()
    def i2c_update(self):
        with SMBus(bus=1, force=True) as bus:
            for register in self.registers:
                for n, v in register.getNewData().items():
                    print(f"{n}: {v}")
                    bus.write_byte_data(self.i2cAddr, n, v.value.uint)

    def data_init(self, path):
        data = pickle.load(open(path, "rb"))
        for register in self.registers:
            # Returned value is a list of 16 bytes
            register.fillData(
                {r: data[r] for r in register.registers}
            )  # Read the value of Port B
            print(str(register) + "\n")

    def exportYaml(self, path, additionalData={}):
        super().exportYaml(
            path,
            {
                "device": "9038Q2M",
                "i2cAddr": self.i2cAddr,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            },
        )
