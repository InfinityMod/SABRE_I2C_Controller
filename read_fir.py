from controllers.ES9038Q2M import DAC_9038Q2M_Control

if __name__ == "__main__":
    lock_settings = [("Mixing, Serial Data and Automute Configuration", "*")]
    mappers = [DAC_9038Q2M_Control(0x48)]
    for m in mappers:
        m.i2c_init()
        print("\n".join([str(min(1.0, (max(-1, float(v)/(2**23))))) for v in m.fir_get(filter="fir1")]))
        print("\n".join([str(min(1.0, (max(-1.0, float(v)/(2**23))))) for v in m.fir_get(filter="fir2")]))