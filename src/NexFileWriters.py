from tkinter import filedialog
from NexFileHeaders import *
from NexFileData import *
from typing import BinaryIO
import json


class NexFileVarType:
    """
    Constants for .nex and .nex5 variable types
    """
    NEURON = 0
    EVENT = 1
    INTERVAL = 2
    WAVEFORM = 3
    POPULATION_VECTOR = 4
    CONTINUOUS = 5
    MARKER = 6


class NexFileWriter:
    def __init__(self):
        pass
        # self.FileHeader: NexFileHeader = NexFileHeader()
        # self.VarHeaders: List[NexVarHeader] = []

    def WriteDataToNexFile(self, fd: FileData, filePath: str):
        """Saves data to .nex file

        Args:
            fd (FileData): file data object
            filePath (str): path of .nex file
        """
        file = open(filePath, "wb")
        fh = NexFileHeader()
        fh.TimestampFrequency = fd.TimestampFrequency
        fh.Comment = fd.Comment
        fh.Beg = fd.SecondsToTicks(fd.StartTimeSeconds)
        fh.End = fd.SecondsToTicks(fd.MaxTimestamp())
        if fh.Beg > 2147483647 or fh.End > 2147483647:
            raise ValueError("Unable to save data in .nex file: maximum timestamp exceeds 2^31")

        fh.NumVars = fd.NumberOfVariables()
        fh.WriteToFile(file)

        BytesInNexFileHeader = 544
        BytesInNexVariableHeader = 208

        dataPos = BytesInNexFileHeader + fd.NumberOfVariables() * BytesInNexVariableHeader

        for var in fd.Neurons:
            vh = NexVarHeader()
            vh.Type = NexFileVarType.NEURON
            vh.Name = var.Name
            vh.Count = len(var.Timestamps)
            vh.WireNumber = var.WireNumber
            vh.UnitNumber = var.UnitNumber
            vh.XPos = var.XPos
            vh.YPos = var.YPos
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += 4 * vh.Count

        for var in fd.Events:
            vh = NexVarHeader()
            vh.Type = NexFileVarType.EVENT
            vh.Name = var.Name
            vh.Count = len(var.Timestamps)
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += 4 * vh.Count

        for var in fd.Intervals:
            vh = NexVarHeader()
            vh.Type = NexFileVarType.INTERVAL
            vh.Name = var.Name
            vh.Count = len(var.IntervalStarts)
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += 8 * vh.Count

        for var in fd.Markers:
            vh = NexVarHeader()
            vh.Type = NexFileVarType.MARKER
            vh.Name = var.Name
            vh.Count = len(var.Timestamps)
            vh.NMarkers = len(var.FieldNames)
            vh.MarkerLength = var.MaxMarkerLength()
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += 4 * vh.Count + vh.NMarkers * 64 + vh.NMarkers * vh.MarkerLength * vh.Count

        for var in fd.Continuous:
            vh = NexVarHeader()
            vh.Type = NexFileVarType.CONTINUOUS
            vh.Name = var.Name
            vh.WFrequency = var.SamplingRate
            vh.Count = len(var.FragmentTimestamps)
            vh.NPointsWave = len(var.Values)
            var.CalculatedScaleFloatsToShorts = CalcScaleFloatsToShorts(var.Values)
            vh.ADtoMV = 1.0 / var.CalculatedScaleFloatsToShorts
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += 8 * vh.Count + vh.NPointsWave * 2

        for var in fd.Waveforms:
            vh = NexVarHeader()
            vh.Type = NexFileVarType.WAVEFORM
            vh.Name = var.Name
            vh.WFrequency = var.SamplingRate
            vh.Count = len(var.Timestamps)
            vh.NPointsWave = var.NumPointsWave
            var.CalculatedScaleFloatsToShorts = CalcScaleFloatsToShorts(var.Values)
            vh.ADtoMV = 1.0 / var.CalculatedScaleFloatsToShorts
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += vh.Count * 4 + vh.Count * vh.NPointsWave * 2

        if dataPos > 4294967295:
            raise ValueError("Unable to save data in .nex file: file size exceeds 2^32")

        for var in fd.Neurons:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int32).tofile(file)

        for var in fd.Events:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int32).tofile(file)

        for var in fd.Intervals:
            np.around(var.IntervalStarts * fd.TimestampFrequency).astype(np.int32).tofile(file)
            np.around(var.IntervalEnds * fd.TimestampFrequency).astype(np.int32).tofile(file)

        for var in fd.Markers:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int32).tofile(file)
            markerLength = var.MaxMarkerLength()
            for i in range(len(var.FieldNames)):
                WriteString(file, var.FieldNames[i], 64)
                if len(var.MarkerValues) > 0:
                    for m in var.MarkerValues[i]:
                        WriteString(file, m, markerLength)

        for var in fd.Continuous:
            np.around(var.FragmentTimestamps * fd.TimestampFrequency).astype(np.int32).tofile(file)
            var.FragmentStartIndexes.astype(np.int32).tofile(file)
            np.around(var.Values * var.CalculatedScaleFloatsToShorts).astype(np.int16).tofile(file)

        for var in fd.Waveforms:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int32).tofile(file)
            np.around(var.Values * var.CalculatedScaleFloatsToShorts).astype(np.int16).tofile(file)

        file.close()


class Nex5FileWriter:
    def __init__(self):
        pass
        # self.FileHeader: NexFileHeader = NexFileHeader()
        # self.VarHeaders: List[NexVarHeader] = []

    def WriteDataToNex5File(self, fd: FileData, filePath: str):
        """Saves data to .nex5 file

        Args:
            fd (FileData): file data object
            filePath (str): path of .nex5 file
        """
        file = open(filePath, "wb")
        fh = Nex5FileHeader()
        fh.Nex5FileVersion = 502
        fh.Comment = fd.Comment
        fh.TimestampFrequency = fd.TimestampFrequency
        fh.RecordingStartTimeInTicks = fd.SecondsToTicks(fd.StartTimeSeconds)
        fh.NumberOfVariables = fd.NumberOfVariables()
        fh.MetadataOffset = 0
        fh.RecordingEndTimeInTicks = fd.SecondsToTicks(fd.MaxTimestamp())
        fh.WriteToFile(file)

        BytesInNex5FileHeader = 356
        BytesInNex5VariableHeader = 244

        dataPos = BytesInNex5FileHeader + fd.NumberOfVariables() * BytesInNex5VariableHeader
        meta = {'variables': []}

        for var in fd.Neurons:
            vh = Nex5VarHeader()
            vh.Type = NexFileVarType.NEURON
            vh.Name = var.Name
            vh.Count = len(var.Timestamps)
            vh.DataOffset = dataPos
            vh.TimestampDataType = 1
            vh.WriteToFile(file)
            dataPos += 8 * vh.Count
            
            varMeta = {'name': var.Name, 'unitNumber': var.UnitNumber}
            varMeta['probe'] = {'position': {'x': var.XPos, 'y': var.YPos}, 'wireNumber' : var.WireNumber}
            meta['variables'].append(varMeta)

        for var in fd.Events:
            vh = Nex5VarHeader()
            vh.Type = NexFileVarType.EVENT
            vh.Name = var.Name
            vh.Count = len(var.Timestamps)
            vh.DataOffset = dataPos
            vh.TimestampDataType = 1
            vh.WriteToFile(file)
            dataPos += 8 * vh.Count

        for var in fd.Intervals:
            vh = Nex5VarHeader()
            vh.Type = NexFileVarType.INTERVAL
            vh.Name = var.Name
            vh.Count = len(var.IntervalStarts)
            vh.TimestampDataType = 1
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += 16 * vh.Count

        for var in fd.Markers:
            vh = Nex5VarHeader()
            vh.Type = NexFileVarType.MARKER
            vh.Name = var.Name
            vh.Count = len(var.Timestamps)
            vh.NumberOfMarkerFields = len(var.FieldNames)
            vh.MarkerLength = var.MaxMarkerLength()
            vh.TimestampDataType = 1
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += 8 * vh.Count + vh.NumberOfMarkerFields * 64 + vh.NumberOfMarkerFields * vh.MarkerLength * vh.Count

        for var in fd.Continuous:
            vh = Nex5VarHeader()
            vh.Type = NexFileVarType.CONTINUOUS
            vh.Name = var.Name
            vh.SamplingFrequency = var.SamplingRate
            vh.TimestampDataType = 1
            vh.ContinuousDataType = 1
            vh.Count = len(var.FragmentTimestamps)
            vh.NumberOfDataPoints = len(var.Values)
            vh.ADtoUnitsCoefficient = 1.0
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += (8 + 4) * vh.Count + vh.NumberOfDataPoints * 4

        for var in fd.Waveforms:
            vh = Nex5VarHeader()
            vh.Type = NexFileVarType.WAVEFORM
            vh.Name = var.Name
            vh.SamplingFrequency = var.SamplingRate
            vh.TimestampDataType = 1
            vh.ContinuousDataType = 1
            vh.Count = len(var.Timestamps)
            vh.NumberOfDataPoints = var.NumPointsWave
            vh.ADtoUnitsCoefficient = 1.0
            vh.DataOffset = dataPos
            vh.WriteToFile(file)
            dataPos += vh.Count * 8 + vh.Count * vh.NumberOfDataPoints * 4
            
            varMeta = {'name': var.Name, 'unitNumber': var.UnitNumber}
            varMeta['probe'] = {'position': {'x': 0, 'y': 0}, 'wireNumber' : var.WireNumber}
            meta['variables'].append(varMeta)


        for var in fd.Neurons:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int64).tofile(file)

        for var in fd.Events:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int64).tofile(file)

        for var in fd.Intervals:
            np.around(var.IntervalStarts * fd.TimestampFrequency).astype(np.int64).tofile(file)
            np.around(var.IntervalEnds * fd.TimestampFrequency).astype(np.int64).tofile(file)

        for var in fd.Markers:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int64).tofile(file)
            markerLength = var.MaxMarkerLength()
            for i in range(len(var.FieldNames)):
                WriteString(file, var.FieldNames[i], 64)
                if len(var.MarkerValues) > 0:
                    for m in var.MarkerValues[i]:
                        WriteString(file, m, markerLength)

        for var in fd.Continuous:
            np.around(var.FragmentTimestamps * fd.TimestampFrequency).astype(np.int64).tofile(file)
            var.FragmentStartIndexes.astype(np.uint32).tofile(file)
            var.Values.astype(np.float32).tofile(file)

        for var in fd.Waveforms:
            np.around(var.Timestamps * fd.TimestampFrequency).astype(np.int64).tofile(file)
            var.Values.astype(np.float32).tofile(file)
        
        # write metadata
        pos = file.tell()
        jsonString = json.dumps(meta)
        file.write(jsonString.encode())
        file.seek( 284)
        file.write(struct.pack('<q', pos))

        file.close()
