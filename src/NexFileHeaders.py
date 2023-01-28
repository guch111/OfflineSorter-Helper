"""
Headers for .nex and .nex5 files
"""
import struct
from typing import BinaryIO

# helper functions


def ReadInt(file: BinaryIO) -> int:
    return struct.unpack('<i', file.read(4))[0]


def ReadInt64(file: BinaryIO) -> int:
    return struct.unpack('<q', file.read(8))[0]


def ReadDouble(file: BinaryIO) -> float:
    return struct.unpack('d', file.read(8))[0]


def ReadString(file: BinaryIO, numBytes: int) -> str:
    return file.read(numBytes).decode('utf-8').strip('\x00')


def WriteInt(file: BinaryIO, theInt: int):
    file.write(struct.pack('<i', theInt))


def WriteInt64(file: BinaryIO, theInt: int):
    file.write(struct.pack('<q', theInt))


def WriteDouble(file: BinaryIO, theDouble: float):
    file.write(struct.pack('d', theDouble))


def WriteString(file: BinaryIO, theString: str, numBytes: int):
    file.write(struct.pack(f'{numBytes}s', theString.encode('utf-8')))


class NexFileHeader:
    """
    Main header in .nex files.
    """

    def __init__(self):

        self.MagicNumber: int = 827868494
        """The first 4 bytes of .nex file. Should be 827868494."""

        self.NexFileVersion: int = 106
        """File version. The last supported version is 106."""

        self.Comment: str = ""
        """File comment. 256 characters max. ASCII encoding is assumed."""

        self.TimestampFrequency: float = 0
        """Timestamps frequency, in Hertz. Timestamp values are stored in ticks, where tick = 1/TimestampFrequency."""

        self.Beg: int = 0
        """Minimum timestamp in file in ticks."""

        self.End: int = 0
        """Maximum timestamp in file in ticks."""

        self.NumVars: int = 0
        """Number of variables in the file. Also, the number of variable headers that follow main file header."""

    def ReadFromFile(self, file: BinaryIO):
        """Reads .nex file header from file.
        Args:
            file (BinaryIO): binary file
        Raises:
            ValueError: if file header is incorrect
        """
        self.MagicNumber = ReadInt(file)
        self.NexFileVersion = ReadInt(file)
        self.Comment = ReadString(file, 256)
        self.TimestampFrequency = ReadDouble(file)
        self.Beg = ReadInt(file)
        self.End = ReadInt(file)
        self.NumVars = ReadInt(file)
        padding = file.read(260)
        if self.MagicNumber != 827868494 or self.TimestampFrequency <= 0:
            raise ValueError('Invalid .nex file')

    def WriteToFile(self, file: BinaryIO):
        """Writes .nex file header to file.
        Args:
            file (BinaryIO): binary file
        """
        WriteInt(file, self.MagicNumber)
        WriteInt(file, self.NexFileVersion)
        WriteString(file, self.Comment, 256)
        WriteDouble(file, self.TimestampFrequency)
        WriteInt(file, self.Beg)
        WriteInt(file, self.End)
        WriteInt(file, self.NumVars)
        file.write(bytearray(260))


class NexVarHeader:
    """
    Variable header in .nex files.
    """

    def __init__(self):
        self.Type: int = 0
        """Variable type. 0 - neuron, 1 - event, 2- interval, 3 - waveform, 4 - pop. vector, 5 - continuously recorded, 6 - marker."""

        self.Version: int = 100
        """Version: almost always should be Version = 100. Use Version = 101 if it is a neuron or waveform variable 
        and WireNumber and UnitNumber are valid.
        Use Version = 102 if it is a waveform variable and PrethresholdTimeInSeconds is valid.
        """

        self.Name = "(no name)"
        """Variable name (64 characters max)."""

        self.DataOffset: int = 0
        """Where the data array for this variable is located in the file."""

        self.Count: int = 0
        """Neuron variable: number of timestamps
        Event variable: number of timestamps
        Interval variable: number of intervals
        Waveform variable: number of waveforms
        Continuous variable: number of fragments
        Population vector: number of weights"""

        self.WireNumber: int = 0
        """Neurons and waveforms only. Channel number from the record header."""

        self.UnitNumber: int = 0
        """Neurons and waveforms only. Unit number from the record header."""

        self.XPos: float = 0
        """Neurons only. X axis electrode position in (0,100) range, used in 3D display."""

        self.YPos: float = 0
        """Neurons only. Y axis electrode position in (0,100) range, used in 3D display."""

        self.WFrequency: float = 0
        """Waveforms and continuous variables only. Sampling frequency in Hertz."""

        self.ADtoMV: float = 0
        """Waveforms and continuous variables only. Coefficient to convert from A/D values to milliVolts."""

        self.NPointsWave: int = 0
        """Waveform variable: number of points in each wave.
        Continuous variable: number of data points."""

        self.NMarkers: int = 0
        """Marker events only. How many values are associated with each marker."""

        self.MarkerLength: int = 0
        """Marker events only. How many characters are in each marker value."""

        self.MVOffset: float = 0
        """Waveforms and continuous variables only.
        This offset is used to convert A/D values in milliVolts:
        valueInMilliVolts = rawValue * ADtoMV + MVOffset"""

        self.PrethresholdTimeInSeconds: float = 0
        """For waveforms, pre-threshold time in seconds. 
        If waveform timestamp in seconds is t,
        then the timestamp of the first point of waveform is t - PrethresholdTimeInSeconds."""

    def ReadFromFile(self, file: BinaryIO):
        """
        Reads .nex file variable header from file.
        Args:
            file (BinaryIO): binary file
        """
        self.Type = ReadInt(file)
        self.Version = ReadInt(file)
        self.Name = ReadString(file, 64)
        self.DataOffset = ReadInt(file)
        self.Count = ReadInt(file)
        self.WireNumber = ReadInt(file)
        self.UnitNumber = ReadInt(file)
        notUsed = ReadInt(file)
        notUsed = ReadInt(file)
        self.XPos = ReadDouble(file)
        self.YPos = ReadDouble(file)
        self.WFrequency = ReadDouble(file)
        self.ADtoMV = ReadDouble(file)
        self.NPointsWave = ReadInt(file)
        self.NMarkers = ReadInt(file)
        self.MarkerLength = ReadInt(file)
        self.MVOffset = ReadDouble(file)
        self.PrethresholdTimeInSeconds = ReadDouble(file)
        padding = file.read(52)

    def WriteToFile(self, file: BinaryIO):
        """Writes .nex variable header to file.
        Args:
            file (BinaryIO):binary file
        """
        WriteInt(file, self.Type)
        WriteInt(file, self.Version)
        WriteString(file, self.Name, 64)
        WriteInt(file, self.DataOffset)
        WriteInt(file, self.Count)
        WriteInt(file, self.WireNumber)
        WriteInt(file, self.UnitNumber)
        file.write(bytearray(8))
        WriteDouble(file, self.XPos)
        WriteDouble(file, self.YPos)
        WriteDouble(file, self.WFrequency)
        WriteDouble(file, self.ADtoMV)
        WriteInt(file, self.NPointsWave)
        WriteInt(file, self.NMarkers)
        WriteInt(file, self.MarkerLength)
        WriteDouble(file, self.MVOffset)
        WriteDouble(file, self.PrethresholdTimeInSeconds)
        file.write(bytearray(52))


class Nex5FileHeader:
    """
    Main header in .nex5 files.
    """

    def __init__(self):
        self.Nex5MagicNumber: int = 894977358
        """First 4 bytes of .nex5 file. String NEX5 as number. Numeric value: 894977358 decimal or 0x3558454e hex."""

        self.Nex5FileVersion: int = 502
        """Valid values are 500, 501 or 502 (Mar-2022).
        If 500, RecordingEndTimeInTicks is not specified,
        501 or greater, RecordingEndTimeInTicks is specified,
        502 or greater, timestamps can be saved as 64-bit integers"""

        self.Comment: str = ""
        """File comment; UTF-8 encoding is assumed. 256 bytes maximum."""

        self.TimestampFrequency: float = 0
        """Timestamps frequency, in Hertz.
        Timestamp values are stored in ticks, where tick = 1/TimestampFrequency."""

        self.RecordingStartTimeInTicks: int = 0
        """Start time when data is imported from a file with non-zero start time."""

        self.NumberOfVariables: int = 0
        """Number of variables in the file, also the number of variable headers that follow .nex5 file header."""

        self.MetadataOffset: int = 0
        """Where the optional metadata for the file and its variables is located in the file.
        Metadata is a string in JSON format."""

        self.RecordingEndTimeInTicks: int = 0
        """The maximum data timestamp across all file variables (file version 501 or greater)"""

    def ReadFromFile(self, file: BinaryIO):
        """
        Reads .nex5 file header.
        Args:
            file (BinaryIO): binary file
        """
        self.Nex5MagicNumber = ReadInt(file)
        self.Nex5FileVersion = ReadInt(file)
        self.Comment = ReadString(file, 256)
        self.TimestampFrequency = ReadDouble(file)
        self.RecordingStartTimeInTicks = ReadInt64(file)
        self.NumberOfVariables = ReadInt(file)
        self.MetadataOffset = ReadInt64(file)
        self.RecordingEndTimeInTicks = ReadInt64(file)
        padding = file.read(56)

        if self.Nex5MagicNumber != 894977358 or self.TimestampFrequency <= 0:
            raise ValueError('Invalid .nex5 file')

    def WriteToFile(self, file: BinaryIO):
        """Writes .nex5 file header to file.
        Args:
            file (BinaryIO): binary file
        """
        WriteInt(file, self.Nex5MagicNumber)
        WriteInt(file, self.Nex5FileVersion)
        WriteString(file, self.Comment, 256)
        WriteDouble(file, self.TimestampFrequency)
        WriteInt64(file, self.RecordingStartTimeInTicks)
        WriteInt(file, self.NumberOfVariables)
        WriteInt64(file, self.MetadataOffset)
        WriteInt64(file, self.RecordingEndTimeInTicks)
        file.write(bytearray(56))


class Nex5VarHeader:
    """
    Variable header in .nex5 files.
    """

    def __init__(self):
        self.Type: int = 0
        """Variable type. 0 - neuron, 1 - event, 2- interval, 3 - waveform, 4 - pop. vector, 5 - continuously recorded, 6 - marker."""

        self.Version: int = 500
        """Variable header version. Should be 500 as of March 2022 (NeuroExplorer version 5.402)."""

        self.Name: str = "(no name)"
        """Variable name. It is assumed that variable names are unique within the file.
        That is, there are no two variables with the same name. There is one reserved name: AllFile.
        NeuroExplorer creates AllFile variable from file data.
        It is an interval variable with a single interval [RecordingStartTimeInTicks, RecordingEndTimeInTicks]."""

        self.DataOffset: int = 0
        """Where the data array for this variable is located in the file."""

        self.Count: int = 0
        """Neuron variable: number of timestamps.
        Event variable: number of timestamps.
        Interval variable: number of intervals.
        Waveform variable: number of waveforms.
        Continuous variable: number of fragments.
        Population vector: number of weights."""

        self.TimestampDataType: int = 0
        """If 0, timestamps are stored as 32-bit integers. If 1, timestamps are stored as 64-bit integers."""

        self.ContinuousDataType: int = 0
        """Waveforms and continuous variables only.
        If 0, waveform and continuous values are stored as 16-bit integers.
        If 1, waveform and continuous values are stored as 32-bit floating point values in units specified in Units field."""

        self.SamplingFrequency: float = 0
        """Waveforms and continuous variables only. Waveform or continuous variable sampling frequency in Hertz."""

        self.Units: str = "mV"
        """Not supported as of March 2022 (version 5.402), milliVolts are assumed. 
        Waveforms and continuous variables only. Units that should be used for the variable values.
        """

        self.ADtoUnitsCoefficient: float = 0
        """Waveforms and continuous variables only. Coefficient to convert from A/D values to units."""

        self.UnitsOffset: float = 0
        """Waveforms and continuous variables only. Used to convert A/D values to units:
        valueInMilliVolts = raw * ADtoUnitsCoefficient + UnitsOffset. 
        Ignored if ContinuousDataType == 1."""

        self.NumberOfDataPoints: int = 0
        """Waveform variable: number of data points in each wave.
        Continuous variable: overall number of data points in the variable."""

        self.PrethresholdTimeInSeconds: float = 0
        """Waveform variables only, pre-threshold time in seconds.
        If waveform timestamp in seconds is t,
        then the timestamp of the first point of waveform is t - PrethresholdTimeInSeconds."""

        self.MarkerDataType: int = 0
        """Marker events only. If 0, marker values are stored as strings.
        If 1, marker values are stored as 32-bit unsigned integers."""

        self.NumberOfMarkerFields: int = 0
        """Marker events only. How many values are associated with each marker."""

        self.MarkerLength: int = 0
        """Marker events only. How many characters are in each string marker value. Ignored if MarkerDataType is 1."""

        self.ContinuousIndexOfFirstPointInFragmentDataType: int = 0
        """Not supported in NeuroExplorer yet (version 5.402). Continuous variables only.
        If 0, indexes of first data point in fragments are stored as unsigned 32-bit integers.
        If 1, indexes of first data point in fragments are stored as unsigned 64-bit integers.
        """

    def ReadFromFile(self, file: BinaryIO):
        """
        Reads .nex5 variable header from file
        Args:
            file (BinaryIO): binary file
        """
        self.Type = ReadInt(file)
        self.Version = ReadInt(file)
        self.Name = ReadString(file, 64)
        self.DataOffset = ReadInt64(file)
        self.Count = ReadInt64(file)
        self.TimestampDataType = ReadInt(file)
        self.ContinuousDataType = ReadInt(file)
        self.SamplingFrequency = ReadDouble(file)
        self.Units = ReadString(file, 32)
        self.ADtoUnitsCoefficient = ReadDouble(file)
        self.UnitsOffset = ReadDouble(file)
        self.NumberOfDataPoints = ReadInt64(file)
        self.PrethresholdTimeInSeconds = ReadDouble(file)
        self.MarkerDataType = ReadInt(file)
        self.NumberOfMarkerFields = ReadInt(file)
        self.MarkerLength = ReadInt(file)
        self.ContinuousIndexOfFirstPointInFragmentDataType = ReadInt(file)
        padding = file.read(60)

    def WriteToFile(self, file: BinaryIO):
        """Writes .nex5 variable header to file
        Args:
            file (BinaryIO):binary file
        """
        WriteInt(file, self.Type)
        WriteInt(file, self.Version)
        WriteString(file, self.Name, 64)
        WriteInt64(file, self.DataOffset)
        WriteInt64(file, self.Count)
        WriteInt(file, self.TimestampDataType)
        WriteInt(file, self.ContinuousDataType)
        WriteDouble(file, self.SamplingFrequency)
        WriteString(file, self.Units, 32)
        WriteDouble(file, self.ADtoUnitsCoefficient)
        WriteDouble(file, self.UnitsOffset)
        WriteInt64(file, self.NumberOfDataPoints)
        WriteDouble(file, self.PrethresholdTimeInSeconds)
        WriteInt(file, self.MarkerDataType)
        WriteInt(file, self.NumberOfMarkerFields)
        WriteInt(file, self.MarkerLength)
        WriteInt(file, self.ContinuousIndexOfFirstPointInFragmentDataType)
        file.write(bytearray(60))
