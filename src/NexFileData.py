"""
Data classes for .nex and .nex5 files.
"""
import numpy as np
from typing import List


def CalcScaleFloatsToShorts(numbers: 'np.ndarray[np.float32]') -> float:
    """Calculates coefficient that can be used to convert float values to shorts (16-bit integers).

    Args:
        numbers (np.ndarray[np.float32]): array of float values

    Returns:
        float: coefficient such that float_value*coefficient is within 16-bit 
                integer range for all values in array.
    """
    theMax = np.amax(numbers)
    theMin = np.amin(numbers)
    absMax = max(abs(theMin), abs(theMax))
    if absMax == 0.0:
        return 1.0
    else:
        return 32767.0 / absMax


class Variable:
    """Base variable class: name only."""

    def __init__(self, name: str = "") -> None:
        self.Name: str = name
        """Variable name."""


class Event(Variable):
    """Event class: name and array of timestamps in seconds."""

    def __init__(self, name: str = "", timestamps: List[float] = []) -> None:
        self.Name: str = name
        """Variable name."""

        self.Timestamps: 'np.ndarray[np.float64]' = np.asarray(timestamps).astype(np.float64)
        """Timestamps in seconds."""

    def MaxTimestamp(self) -> float:
        """Returns maximum timestamp in seconds."""
        if self.Timestamps is None or len(self.Timestamps) == 0:
            return 0
        return self.Timestamps[-1]


class Neuron(Event):
    """
    Neuron class: event data plus wire, unit and position data.
    """

    def __init__(self, name: str = "", timestamps: List[float] = []) -> None:
        self.Name: str = name
        """Variable name."""

        self.Timestamps: 'np.ndarray[np.float64]' = np.asarray(timestamps).astype(np.float64)
        """Timestamps in seconds."""

        self.WireNumber: int = 0
        """Wire (electrode) number."""

        self.UnitNumber: int = 0
        """Unit or cluster number."""

        self.XPos: float = 0
        """X axis electrode position in (0,100) range, used in 3D display."""

        self.YPos: float = 0
        """Y axis electrode position in (0,100) range, used in 3D display."""


class Marker(Event):
    """Markers are events with associated strings or integers."""

    def __init__(self, name: str = "", timestamps: List[float] = [],
                 fieldNames: List[str] = [], markerValues: List[List[str]] = []) -> None:
        self.Name: str = name
        """Variable name."""

        self.Timestamps: 'np.ndarray[np.float64]' = np.asarray(timestamps).astype(np.float64)
        """Timestamps in seconds."""

        self.FieldNames: List[str] = fieldNames
        """Each timestamp can have several strings or integers associated with it (several fields). These are filed names."""

        self.MarkerValues: List[List[str]] = markerValues
        """Each timestamp can have several strings or integers associated with it (several fields).
        Each sublist contains string values for a specific marker field."""

        self.MarkerValuesAsUnsignedIntegers = [[]]
        """List of np arrays. Each list element contains numeric values for a specific marker field."""

    def MaxMarkerLength(self):
        """Returns maximum length of all string marker values."""
        maxLen = 0
        if len(self.MarkerValues) > 0:
            for fieldValues in self.MarkerValues:
                for m in fieldValues:
                    maxLen = max(maxLen, len(m))
            return maxLen
        else:
            for fieldValues in self.MarkerValuesAsUnsignedIntegers:
                for m in fieldValues:
                    maxLen = max(maxLen, len(str(m)))
            return maxLen


class Interval(Variable):
    """Interval class. Has two arrays: interval starts and interval ends in seconds."""

    def __init__(self, name: str = "", starts: List[float] = [], ends: List[float] = []) -> None:
        self.Name: str = name
        """Variable name."""

        self.IntervalStarts: 'np.ndarray[np.float64]' = np.asarray(starts).astype(np.float64)
        """Interval start times in seconds."""

        self.IntervalEnds: 'np.ndarray[np.float64]' = np.asarray(ends).astype(np.float64)
        """Interval end times in seconds."""

    def MaxTimestamp(self) -> float:
        """Returns maximum timestamp in seconds."""
        if self.IntervalEnds is None or len(self.IntervalEnds) == 0:
            return 0
        return self.IntervalEnds[-1]


class Continuous(Variable):
    """ Continuous class. 
        Contains: (1) Sampling rate in Hz. (2) Array of timestamps in seconds (each timestamp is for the beginning of the fragment).
                (3) Array of indexes (each index is the position of the first data point of the fragment in the a/d array).
                (4) Array of all a/d values in milliVolts.
    """

    def __init__(self, name: str = "", samplingRate: float = 0, fragmentStarts: List[float] = [],
                 fragmentStartIndexes: List[int] = [],
                 values: List[float] = []) -> None:
        self.Name: str = name
        """Variable name."""

        self.SamplingRate: float = samplingRate
        """Sampling rate in Hz."""

        self.FragmentTimestamps: 'np.ndarray[np.float64]' = np.asarray(fragmentStarts).astype(np.float64)
        """Array of timestamps in seconds (each timestamp is for the beginning of the fragment)."""

        self.FragmentStartIndexes: 'np.ndarray[np.uint32]' = np.asarray(fragmentStartIndexes).astype(np.uint32)
        """Array of indexes (each index is the position of the first data point of the fragment in the a/d array)."""

        self.Values: 'np.ndarray[np.float32]' = np.asarray(values).astype(np.float32)
        """Array of all a/d values in milliVolts."""

        self.CalculatedScaleFloatsToShorts = 1
        """When saving data to .nex file, this field contains coefficient to convert floats to shorts."""

    def MaxTimestamp(self) -> float:
        """Returns maximum timestamp in seconds (the last timestamp of all continuous values)."""
        if self.FragmentTimestamps is None or len(self.FragmentTimestamps) == 0 or self.SamplingRate <= 0:
            return 0
        if self.FragmentStartIndexes is None or len(self.FragmentStartIndexes) == 0 or self.Values is None or len(self.Values) == 0:
            return 0
        step = 1.0/self.SamplingRate
        return self.FragmentTimestamps[-1] + step * (len(self.Values) - self.FragmentStartIndexes[-1] - 1.0)


class Waveform(Event):
    """ Waveform class. 
        Contains: Sampling rate in Hz
                Number of points in each wave
                Array of timestamps in seconds (each timestamp is for the beginning of the waveform).
                Array of all waveform a/d values in milliVolts.
    """

    def __init__(self, name: str = "", samplingRate: float = 0, timestamps: List[float] = [],
                 numPointsWave: int = 0, values: List[float] = []):
        self.Name: str = name
        """Variable name."""

        self.SamplingRate: float = samplingRate
        """Sampling rate in Hz."""

        self.Timestamps: 'np.ndarray[np.float64]' = np.asarray(timestamps).astype(np.float64)
        """Timestamps in seconds."""

        self.WireNumber: int = 0
        """Wire (electrode) number."""

        self.UnitNumber: int = 0
        """Unit or cluster number."""

        self.NumPointsWave: int = numPointsWave
        """Number of data point in each wave."""

        self.Values: 'np.ndarray[np.float32]' = np.asarray(values).astype(np.float32)
        """Waveform values in milliVolts."""

        self.Values = self.Values.reshape((len(self.Timestamps), self.NumPointsWave))

        self.CalculatedScaleFloatsToShorts = 1
        """When saving data to .nex file, this field contains coefficient to convert floats to shorts."""

    def MaxTimestamp(self) -> float:
        """Returns maximum timestamp in seconds (the last timestamp of the last waveform)."""
        if self.Timestamps is None or len(self.Timestamps) == 0 or self.SamplingRate <= 0 or self.NumPointsWave == 0:
            return 0
        step = 1.0/self.SamplingRate
        return self.Timestamps[-1] + step * (self.NumPointsWave - 1.0)


class FileData:
    """
    FileData object. Contains arrays of data variables.
    """

    def __init__(self) -> None:
        self.Comment: str = ""
        """File comment."""

        self.TimestampFrequency: float = 0
        """Timestamps frequency, in Hertz. Timestamp values in .net and .nex5 files are stored in ticks, where tick = 1/TimestampFrequency."""

        self.StartTimeSeconds: float = 0
        """Start time in seconds."""

        self.EndTimeSeconds: float = 0
        """End time in seconds."""

        self.Events: List[Event] = []
        """List of Events."""

        self.Neurons: List[Neuron] = []
        """List of Neurons."""

        self.Intervals: List[Interval] = []
        """List of intervals."""

        self.Markers: List[Marker] = []
        """List of Markers."""

        self.Continuous: List[Continuous] = []
        """List of Continuous variables."""

        self.Waveforms: List[Waveform] = []
        """List of Waveform variables."""

    def NumberOfVariables(self) -> int:
        """Returns number of all variables"""
        return len(self.Neurons) + len(self.Events) + len(self.Intervals) + len(self.Markers) + len(self.Continuous) + len(self.Waveforms)

    def MaxTimestamp(self) -> float:
        """Returns maximum timestamp of all variables in seconds."""
        maxTs = 0
        for v in self.Neurons:
            maxTs = max(maxTs, v.MaxTimestamp())
        for v in self.Events:
            maxTs = max(maxTs, v.MaxTimestamp())
        for v in self.Intervals:
            maxTs = max(maxTs, v.MaxTimestamp())
        for v in self.Markers:
            maxTs = max(maxTs, v.MaxTimestamp())
        for v in self.Continuous:
            maxTs = max(maxTs, v.MaxTimestamp())
        for v in self.Waveforms:
            maxTs = max(maxTs, v.MaxTimestamp())
        return maxTs

    def TicksToSeconds(self, ticks: int) -> float:
        """Converts time in thicks to time in seconds."""
        return ticks/self.TimestampFrequency

    def SecondsToTicks(self, seconds: float) -> int:
        """Converts time in seconds to time in ticks."""
        return round(seconds * self.TimestampFrequency)
