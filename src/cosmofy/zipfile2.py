"""Enhanced `ZipFile`"""

# std
from __future__ import annotations
from datetime import datetime
from fnmatch import fnmatch
from operator import attrgetter
from typing import Union
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
from zipfile import ZipInfo
import logging


log = logging.getLogger(__name__)
now = datetime.now()


class ZipFile2(ZipFile):
    """Extension of `zipfile.ZipFile` that allows removing members."""

    _writing: bool

    # NOTE: This function only works on python >= 3.11
    # def add_dir(self, name: str, mode: int = 0o777, date: datetime = now) -> ZipFile2:
    #     """Add a directory to an archive with permissions."""
    #     if not name.endswith("/"):
    #         name += "/"
    #     info = ZipInfo(name, date.timetuple()[:6])
    #     info.compress_size = 0
    #     info.CRC = 0
    #     info.external_attr = ((0o40000 | mode) & 0xFFFF) << 16
    #     info.external_attr |= 0x10
    #     info.file_size = 0
    #     info.flag_bits |= 0x800
    #     self.mkdir(info)
    #     return self

    def add_file(
        self,
        path: str,
        data: Union[bytearray, bytes, str],
        mode: int = 0o644,
        date: datetime = now,
    ) -> ZipFile2:
        """Add a file to an archive with appropriate permissions."""
        info = ZipInfo(path, date.timetuple()[:6])
        info.compress_type = ZIP_DEFLATED
        info.external_attr = (0x8000 | (mode & 0xFFFF)) << 16
        info.flag_bits |= 0x800
        self.writestr(info, data)
        return self

    # https://github.com/python/cpython/commit/659eb048cc9cac73c46349eb29845bc5cd630f09
    def remove(self, member: Union[str, ZipInfo]) -> ZipFile2:
        """Remove a file from the archive. The archive must be open with mode 'a'"""
        if self.mode != "a":
            raise RuntimeError("remove() requires mode 'a'")
        if not self.fp:
            raise ValueError("Attempt to write to ZIP archive that was already closed")
        if self._writing:
            raise ValueError(
                "Can't write to ZIP archive while an open writing handle exists."
            )

        # zinfo
        if isinstance(member, ZipInfo):
            return self._remove_member(member)

        # name
        if "*" not in member and "?" not in member:
            return self._remove_member(self.getinfo(member))

        # glob
        for item in self.filelist:
            if fnmatch(item.filename, member):
                self._remove_member(item)
        return self

    def _remove_member(self, member: ZipInfo) -> ZipFile2:
        """Internal method to remove a member."""
        fp = self.fp
        assert fp

        # sort by header_offset in case central dir has different order
        entry_offset = 0
        filelist = sorted(self.filelist, key=attrgetter("header_offset"))
        last_index = len(filelist) - 1
        for i, info in enumerate(filelist):
            if info.header_offset < member.header_offset:  # keep going until target
                continue

            # get the total size of the entry
            entry_size = None
            if i == last_index:
                entry_size = self.start_dir - info.header_offset
            else:
                entry_size = filelist[i + 1].header_offset - info.header_offset

            if member == info:  # set the entry offset
                entry_offset = entry_size
                continue
            # move all subsequent entries

            # read the actual entry data
            fp.seek(info.header_offset)
            entry_data = fp.read(entry_size)

            # update the header
            info.header_offset -= entry_offset

            # write the entry to the new position
            fp.seek(info.header_offset)
            fp.write(entry_data)
            fp.flush()

        # update state
        self.start_dir -= entry_offset
        self.filelist.remove(member)
        del self.NameToInfo[member.filename]
        self._didModify = True

        # seek to the start of the central dir
        fp.seek(self.start_dir)
        return self

    def _write_end_record(self) -> None:
        """Write the end record to the file and truncate extra space."""
        super()._write_end_record()  # type: ignore
        if self.fp and hasattr(self.fp, "truncate"):
            self.fp.truncate()
        else:  # pragma: no cover
            # This is hard to test without messing up other things.
            print(
                "WARNING: truncate unimplemented, zip WILL be corrupted if you removed a member!"
            )
