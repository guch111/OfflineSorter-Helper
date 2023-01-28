from re import X
from NexFileHeaders import *
from NexFileData import *
from typing import BinaryIO
import json
from types import SimpleNamespace
import os


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

    

class NexFileReader:
    def __init__(self):
        self.FileHeader: NexFileHeader = NexFileHeader()
        self.VarHeaders: List[NexVarHeader] = []
    
    def ReadNexFile(self, filePath: str) -> FileData:
        """Reads data from .nex file
        Args:
            filePath: path of .nex file
        Raises:
            ValueError: if file header is incorrect or cannot read all data
        """
        fd = FileData()
        file = open(filePath, "rb")
        
        self.FileHeader.ReadFromFile(file)
        fd.Comment = self.FileHeader.Comment
        fd.TimestampFrequency = self.FileHeader.TimestampFrequency
        fd.StartTimeSeconds = fd.TicksToSeconds(self.FileHeader.Beg)
        fd.EndTimeSeconds = fd.TicksToSeconds(self.FileHeader.End)
        
        # read variable headers
        for i in range(self.FileHeader.NumVars):
            vh = NexVarHeader()
            vh.ReadFromFile(file)
            self.VarHeaders.append(vh)
            
        # read variable data
        for vh in self.VarHeaders:
            if vh.Type == NexFileVarType.NEURON:
                neuron = Neuron(vh.Name)
                neuron.WireNumber = vh.WireNumber
                neuron.UnitNumber = vh.UnitNumber
                neuron.XPos = vh.XPos
                neuron.YPos = vh.YPos
                file.seek(vh.DataOffset)
                neuron.Timestamps = np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
                fd.Neurons.append(neuron)
            
            elif vh.Type == NexFileVarType.EVENT:
                event = Event(vh.Name)
                file.seek(vh.DataOffset)
                event.Timestamps = np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
                fd.Events.append(event)
            
            elif vh.Type == NexFileVarType.INTERVAL:
                interval = Interval(vh.Name)
                file.seek(vh.DataOffset)
                interval.IntervalStarts = np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
                interval.IntervalEnds = np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
                fd.Intervals.append(interval)
            
            elif vh.Type == NexFileVarType.MARKER:
                marker = Marker(vh.Name)
                file.seek(vh.DataOffset)
                marker.Timestamps = np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
                for field in range(vh.NMarkers):
                    marker.FieldNames.append(file.read(64).decode().strip('\x00').strip())
                    marker.MarkerValues.append([file.read(vh.MarkerLength).decode().strip('\x00') for m in range(vh.Count)])
                fd.Markers.append(marker)
            
            elif vh.Type == NexFileVarType.CONTINUOUS:
                cont = Continuous(vh.Name)
                cont.SamplingRate = vh.WFrequency
                file.seek(vh.DataOffset)
                cont.FragmentTimestamps = np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
                cont.FragmentStartIndexes = np.fromfile(file, np.int32, vh.Count).astype(np.uint32)
                raw = np.fromfile(file, np.int16, vh.NPointsWave)
                cont.Values = raw.astype(np.float32)*vh.ADtoMV + vh.MVOffset
                fd.Continuous.append(cont)
            
            elif vh.Type == NexFileVarType.WAVEFORM:
                wave = Waveform(vh.Name)
                wave.SamplingRate = vh.WFrequency
                wave.NumPointsWave = vh.NPointsWave
                file.seek(vh.DataOffset)
                wave.Timestamps = np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
                raw = np.fromfile(file, np.int16, vh.NPointsWave*vh.Count)
                wave.Values = raw.astype(np.float32)*vh.ADtoMV + vh.MVOffset
                wave.Values = wave.Values.reshape((vh.Count, vh.NPointsWave))
                fd.Waveforms.append(wave)

        file.close()
        return fd
 

class Nex5FileReader:
    def __init__(self):
        self.FileHeader: Nex5FileHeader = Nex5FileHeader()
        self.VarHeaders: List[Nex5VarHeader] = []
    
    def _ReadTimestamps(self, vh: Nex5VarHeader, fd: FileData, file):
        if vh.TimestampDataType == 0:
            return np.fromfile(file, np.int32, vh.Count)/fd.TimestampFrequency
        else:
            return np.fromfile(file, np.int64, vh.Count)/fd.TimestampFrequency
    
    def ReadNex5File(self, filePath: str) -> FileData:
        """Reads data from .nex5 file.
        Args:
            filePath: path of .nex5 file.
        Raises:
            ValueError: if file header is incorrect or cannot read all data.
        """
        fd = FileData()
        file = open(filePath, "rb")
        self.FileHeader.ReadFromFile(file)
        fd.Comment = self.FileHeader.Comment
        fd.TimestampFrequency = self.FileHeader.TimestampFrequency
        fd.StartTimeSeconds = fd.TicksToSeconds(self.FileHeader.RecordingStartTimeInTicks)
        fd.EndTimeSeconds = fd.TicksToSeconds(self.FileHeader.RecordingEndTimeInTicks)

        # read variable headers
        for i in range(self.FileHeader.NumberOfVariables):
            vh = Nex5VarHeader()
            vh.ReadFromFile(file)
            self.VarHeaders.append(vh)

        # read variable data
        for vh in self.VarHeaders:
            if vh.Type == NexFileVarType.NEURON:
                neuron = Neuron(vh.Name)
                file.seek(vh.DataOffset)
                neuron.Timestamps = self._ReadTimestamps(vh, fd, file)
                fd.Neurons.append(neuron)
            
            elif vh.Type == NexFileVarType.EVENT:
                event = Event(vh.Name)
                file.seek(vh.DataOffset)
                event.Timestamps = self._ReadTimestamps(vh, fd, file)
                fd.Events.append(event)
            
            elif vh.Type == NexFileVarType.INTERVAL:
                interval = Interval(vh.Name)
                file.seek(vh.DataOffset)
                interval.IntervalStarts = self._ReadTimestamps(vh, fd, file)
                interval.IntervalEnds = self._ReadTimestamps(vh, fd, file)
                fd.Intervals.append(interval)
            
            elif vh.Type == NexFileVarType.MARKER:
                marker = Marker(vh.Name)
                file.seek(vh.DataOffset)
                marker.MarkerValues.clear()
                marker.MarkerValuesAsUnsignedIntegers.clear()
                marker.Timestamps = self._ReadTimestamps(vh, fd, file)
                for field in range(vh.NumberOfMarkerFields):
                    marker.FieldNames.append(file.read(64).decode().strip('\x00').strip())
                    if vh.MarkerDataType == 0:
                        marker.MarkerValues.append([file.read(vh.MarkerLength).decode().strip('\x00') for m in range(vh.Count)])
                    else:
                        marker.MarkerValuesAsUnsignedIntegers.append( np.fromfile(file, np.uint32, vh.Count))
                fd.Markers.append(marker)
            
            elif vh.Type == NexFileVarType.CONTINUOUS:
                cont = Continuous(vh.Name)
                cont.SamplingRate = vh.SamplingFrequency
                file.seek(vh.DataOffset)
                cont.FragmentTimestamps = self._ReadTimestamps(vh, fd, file)
                cont.FragmentStartIndexes = np.fromfile(file, np.uint32, vh.Count)
                if vh.ContinuousDataType == 0:
                    raw = np.fromfile(file, np.int16, vh.NumberOfDataPoints)
                    cont.Values = raw.astype(np.float32)*vh.ADtoUnitsCoefficient + vh.UnitsOffset
                else:
                    cont.Values = np.fromfile(file, np.float32, vh.NumberOfDataPoints)
                fd.Continuous.append(cont)
            
            elif vh.Type == NexFileVarType.WAVEFORM:
                wave = Waveform(vh.Name)
                wave.SamplingRate = vh.SamplingFrequency
                wave.NumPointsWave = vh.NumberOfDataPoints
                file.seek(vh.DataOffset)
                wave.Timestamps = self._ReadTimestamps(vh, fd, file)
                if vh.ContinuousDataType == 0:
                    raw = np.fromfile(file, np.int16, vh.NumberOfDataPoints*vh.Count)
                    wave.Values = raw.astype(np.float32)*vh.ADtoUnitsCoefficient + vh.UnitsOffset
                    wave.Values = wave.Values.reshape((vh.Count, vh.NumberOfDataPoints))
                else:
                    wave.Values = np.fromfile(file, np.float32, vh.NumberOfDataPoints*vh.Count)
                    wave.Values = wave.Values.reshape((vh.Count, vh.NumberOfDataPoints))
                fd.Waveforms.append(wave)
                
        #  read metadata
        fileSize = os.path.getsize(filePath)
        if self.FileHeader.MetadataOffset > 0 and self.FileHeader.MetadataOffset < fileSize:
            try:
                file.seek(self.FileHeader.MetadataOffset)
                jsonString = file.read(fileSize - self.FileHeader.MetadataOffset).decode().strip('\0x00')
                meta = json.loads(jsonString)
                varMeta = meta.get('variables', [])
                for vm in varMeta:
                    name = vm.get('name', '')
                    if name:
                        unit = vm.get('unitNumber', 0)
                        wire = vm.get('probe', {}).get('wireNumber', 0)
                        x = vm.get('probe', {}).get('position', {}).get('x', 0)
                        y = vm.get('probe', {}).get('position', {}).get('y', 0)
                        for n in fd.Neurons:
                            if n.Name == name:
                                n.UnitNumber = unit
                                n.WireNumber = wire
                                n.XPos = x
                                n.YPos = y
                                break
                        for w in fd.Waveforms:
                            if w.Name == name:
                                w.UnitNumber = unit
                                w.WireNumber = wire
                                break
                                
            except Exception as ex:
                print(jsonString)
                print(ex)
                
        
        file.close()       
        return fd
    
