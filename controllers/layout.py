from __future__ import annotations
import math, pickle, yaml
from typing import Union
from bitstring import BitArray


class Bin(object):
    def __init__(self, num, registerLen=8, joinDirection="left", idxBegin="right", mode="unsigned"):
        self.registerLen = registerLen
        self.joinDirection = joinDirection
        self.idxBegin = idxBegin
        self.mode = mode
        
        args = {}
        if isinstance(num, int):
            if mode == "signed":
                args["int"] = num
            elif mode == "unsigned":
                args["uint"] = num
            args["length"] = registerLen
            self.value: BitArray = BitArray(**args)
        elif isinstance(num, BitArray):
            self.value: BitArray = BitArray(uint = 0, length = registerLen)
            self[0:num.length] = num
        elif isinstance(num, Bin):
            self.value: BitArray = BitArray(uint=0, length = registerLen)
            self[0:num.value.length] = num.value
        elif isinstance(num, str):
            self.value: BitArray = BitArray(bin=num)
        else:
            raise("Wrong data type")

    def join(self, bin2):
        n1 = self.value.copy()
        n2 = bin2.value
        
        if self.joinDirection == "left":
            n1.prepend(n2)
            return Bin(
                n1,
                registerLen=n1.length,
                joinDirection=self.joinDirection,
                idxBegin=self.idxBegin,
            )
        else:
            n1.append(n2)
            return Bin(
                n1,
                registerLen=n1.length,
                joinDirection=self.joinDirection,
                idxBegin=self.idxBegin,
            )

    def readRange(self, start: int, stop: int):
        reverse = False
        _var = self.value.copy()
        if start > stop:
            start, stop = stop, start
            reverse = True
        if self.idxBegin == "right":
            _var.reverse()
            _var = _var[start:stop]
            reverse = not reverse
        elif self.idxBegin == "left":
            _var = self.value[start:stop]
        if reverse:
            _var.reverse() 
        return Bin(
            _var,
            registerLen=_var.length,
            joinDirection=self.joinDirection,
            idxBegin=self.idxBegin,
        )

    def applyData(self, start: int, stop: int, data):
        # check if data contains more information than range can give
        _len = stop - start
       
        if isinstance(data, Bin):
            data = data.value.copy()
        elif isinstance(data, BitArray):
            data = data.copy()
        assert _len >= data.length

        if start > stop:
            start, stop = stop, start
            data.reverse()

        data = data[:_len]
        if self.idxBegin == "right":
            self.value.reverse()
            data.reverse()
        self.value.overwrite(data, start)
        if self.idxBegin == "right":
            self.value.reverse()

        return self

    @property
    def int(self):
        if self.mode == "signed":
            return self.value.int
        if self.mode == "unsigned":
            return self.value.uint

    @property
    def bin(self):
        return self.value.bin

    def __eq__(self, v):
        return self.value.int == v.value.int

    def __ne__(self, v):
        return self.value.int != v.value.int

    def __int__(self):
        return self.int

    def __str__(self):
        return self.value.bin

    def __len__(self):
        return self.value.length

    def __getitem__(self, subscript):
        value = self.value.copy()
        if self.idxBegin == "right":
            value.reverse()
        if isinstance(subscript, slice):
            value = value[subscript.start : subscript.stop : subscript.step]
        elif isinstance(subscript, tuple):
            value = value[subscript[0] : subscript[1]]
        elif isinstance(subscript, int):
            # Do your handling for a plain index
            value = value[subscript]
        if self.idxBegin == "right":
            value.reverse()
        return Bin(value,
            mode=self.mode,
            registerLen=value.length,
            joinDirection=self.joinDirection,
            idxBegin=self.idxBegin)

    def __setitem__(self, subscript, value):
        if isinstance(value, str):
            value = BitArray(bin=value)

        self.applyData(subscript.start, subscript.start+value.length, value)

    def copy(self):
        return Bin(self.value,
            mode=self.mode,
            registerLen=self.registerLen,
            joinDirection=self.joinDirection,
            idxBegin=self.idxBegin)

class I2CMapper:
    def __init__(self):
        self.registers = []
        self.registerNames = []

    class mnemonicMapper:
        def __init__(self, name: str, mapping: dict, description: str = ""):
            self._value = Bin(0)
            self.name = name
            self.mapping = mapping
            self.description = description
            if len(mapping)>0:
                self.value = list(mapping.keys())[0]  
        @property
        def possible_values(self):
            return list(self.mapping.keys())

        @property
        def raw_value(self):
            return self._value

        @property
        def value(self):
            for n, v in self.mapping.items():
                if v == self._value:
                    return n
            return "Reserved"

        @value.setter
        def value(self, value):
            if isinstance(value, Bin):
                self._value.applyData(0, len(value), value)
            elif value in self.mapping:
                self._value = self.mapping[value].copy()

    class mnemonicFN:
        def __init__(self, name: str, mapping: dict, description: str = ""):
            self.name = name
            self.mapping = mapping
            self.description = description
            self.value = 0

        @property
        def possible_values(self):
            return []

        @property
        def raw_value(self):
            return self._value

        @property
        def value(self):
            return self.mapping["out"](self._value)

        @value.setter
        def value(self, value):
            if isinstance(value, Bin):
                self._value.applyData(0, len(value), value)
            else:
                self._value = self.mapping["in"](value)

    class registerRange:
        def __init__(self, start, stop, registerID=0, registerLen=8):
            self.registerLen = registerLen
            self.range = (start, stop, registerID)

        def getRangeData(self, rawStreams: dict):
            dataStream = None
            for r in [self.range]:
                assert r[2] in rawStreams
                if dataStream is None:
                    dataStream = rawStreams[r[2]].readRange(r[0], r[1] + 1)
                else:
                    dataStream = dataStream.join(
                        rawStreams[r[2]].readRange(r[0], r[1] + 1)
                    )
            return dataStream

        def applyUpdate(self, rawStream: dict, data: Bin):
            for r in [self.range]:
                assert r[2] in rawStream
                rawStream[r[2]].applyData(r[0], r[1] + 1, data)
            return self

        def containsRegister(self, registerID):
            return (self.range[2] == registerID)

    class registerMultiRange:
        def __init__(self, start, stop, registerID=0, registerLen=8):
            self.ranges = []
            self.start = start
            self.stop = stop
            self.registerLen = registerLen
            self.registerID = registerID

            registerRange = range(int(start / registerLen), int(stop / registerLen) + 1)
            if registerID == "all":
                for i, r in enumerate(registerRange):
                    self.add(
                        max(0, start - r * registerLen),
                        min(registerLen - 1, (stop - r * registerLen)),
                        registerID=r,
                    )
            else:
                self.add(start, stop, registerID=registerID)

        def add(self, start, stop, registerID=0):
            self.ranges.append((start, stop, registerID))
            return self

        def getRangeData(self, rawStreams: dict):
            dataStream = None
            for r in self.ranges:
                assert r[2] in rawStreams
                if dataStream is None:
                    dataStream = rawStreams[r[2]].readRange(r[0], r[1] + 1)
                else:
                    dataStream = dataStream.join(
                        rawStreams[r[2]].readRange(r[0], r[1] + 1)
                    )
            return dataStream

        def updateRegister(self, registers):
            for i in range(len(self.ranges)):
                self.ranges[i] = tuple(
                    list(self.ranges[i][:2]) + [registers[self.ranges[i][2]]]
                )

        def applyUpdate(self, rawStream: dict, data: Bin):
            offset = 0
            for r in self.ranges:
                assert r[2] in rawStream
                rawStream[r[2]].applyData(
                        r[0], r[1] + 1, data[offset, (r[1]-r[0]) + offset + 1]
                )
                offset += (r[1] - r[0]) + 1
            return self

        def containsRegister(self, registerID):
            return any([r[2] == registerID for r in self.ranges])

    class register:
        def __init__(self, registers, name, writeable=True, registerLen=8):
            self.registers = (
                registers if isinstance(registers, tuple) else tuple([registers])
            )
            self.writeable = writeable
            self.registerLen = registerLen
            self.mnemonics = []
            self.name = name
            self.rawData = {r:Bin(0, registerLen=8) for r in (registers if isinstance(registers, tuple) else [registers])}
            self.updateRanges = []
            self.initOver = True

        def __str__(self):
            _str = ["Register {0}: {1}".format(str(self.registers), self.name)]
            for m in self.mnemonics:
                _str.append("{0}: {1}".format(m["mapper"].name, m["mapper"].value))
            _str.append(
                "Raw: \n{}".format(
                    "\n".join(
                        [
                            "{0}: {1}".format(n, Bin(v).value.bin)
                            for n, v in self.rawData.items()
                        ]
                    )
                )
            )
            return "\n".join(_str)

        def __getattr__(self, name):
            if name in self.__dict__:
                return super().__getattribute__(name)
            return self.get(name).value

        def __setattr__(self, name, value):
            if name not in ["rawData", "updateRanges"] and (
                "initOver" in self.__dict__ and self.__dict__["initOver"]
            ):
                found = False
                if self.writeable:
                    for m in self.mnemonics:
                        if m["mapper"].name == name:
                            m["mapper"].value = value
                            self.updateData(m["range"], m["mapper"].raw_value)
                            if m["range"] not in self.updateRanges:
                                self.updateRanges.append(m["range"])
                            found = True
                            break
                assert found
            else:
                super().__setattr__(name, value)

        @property
        def mnemonicNames(self):
            return [m["mapper"].name for m in self.mnemonics]

        def get(self, name):
            for m in self.mnemonics:
                if m["mapper"].name == name:
                    return m["mapper"]
            assert False
            return None

        def fillData(self, data):
            self.rawData = data
            for m in self.mnemonics:
                m["mapper"].value = m["range"].getRangeData(self.rawData)

        def updateData(self, range, newData):
            range.applyUpdate(self.rawData, newData)
            self.fillData(self.rawData)

        def getNewData(self):
            update_registers = []
            for r in self.updateRanges:
                if isinstance(r, I2CMapper.registerRange):
                    update_registers += [r.range[2]]
                elif isinstance(r, I2CMapper.registerMultiRange):
                    update_registers += [_r[2] for _r in r.ranges]
            self.updateRanges = []
            return {r: self.rawData[r] for r in set(update_registers)}

        # def addMnemonic(self, range: Union[I2CMapper.registerRange, I2CMapper.registerMultiRange], mapper: I2CMapper.mnemonicMapper):
        def addMnemonic(self, range, mapper):
            if isinstance(range, I2CMapper.registerMultiRange):
                if range.registerID == "all":
                    range.updateRegister(self.registers)
            self.mnemonics.append({"range": range, "mapper": mapper})
            return self

    def updateRegisterNames(self):
        self.registerNames = [r.name for r in self.registers]

    def exportYaml(self, path, additionalData={}):
        data = {}
        for r in self.registers:
            data["reg_" + "_".join(map(str, r.registers))] = {
                "name": r.name or "",
                "writeable": r.writeable,
                "registerLen": r.registerLen,
                "rawData": dict(
                    map(lambda kv: (kv[0], kv[1].value.bin), r.rawData.items())
                ),
                "mnemonics": {
                    m["mapper"].name: {
                        "value": m["mapper"].value,
                        "possible_values": m["mapper"].possible_values,
                    }
                    for m in r.mnemonics
                },
            }
        data = {**data, **additionalData}
        with open(path, "w") as outfile:
            yaml.dump(data, outfile, default_flow_style=False)

    def importYaml(self, path):
        with open(path, "r") as infile:
            data = yaml.load(infile)
            for n, v in data.items():
                if n.startswith("reg_"):
                    register = self.get(v["name"])
                    if register.writeable:
                        register.fillData({k: Bin(v, registerLen=8) for k, v in v["rawData"].items()})
                        for n0, v0 in v["mnemonics"].items():
                            if n0 != "reserved":
                                setattr(register, n0, v0["value"])

    def get(self, registerName):
        for r in self.registers:
            if r.name == registerName:
                return r
        return None