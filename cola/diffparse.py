import os
import re

from cola import utils
from cola import gitcmds


class DiffParser(object):
    """Handles parsing diff for use by the interactive index editor."""
    def __init__(self, model, filename='',
                 cached=True, branch=None, reverse=False):

        self._header_re = re.compile('^@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*')
        self._headers = []

        self._idx = -1
        self._diffs = []
        self._diff_spans = []
        self._diff_offsets = []

        self.start = None
        self.end = None
        self.offset = None
        self.diffs = []
        self.selected = []

        (header, diff) = gitcmds.diff_helper(filename=filename,
                                             branch=branch,
                                             with_diff_header=True,
                                             cached=cached and not bool(branch),
                                             reverse=cached or bool(branch) or reverse)
        self.model = model
        self.diff = diff
        self.header = header
        self.parse_diff(diff)

        # Always index into the non-reversed diff
        self.fwd_header, self.fwd_diff = \
            gitcmds.diff_helper(filename=filename,
                                branch=branch,
                                with_diff_header=True,
                                cached=cached and not bool(branch),
                                reverse=bool(branch))

    def write_diff(self,filename,which,selected=False,noop=False):
        """Writes a new diff corresponding to the user's selection."""
        if not noop and which < len(self.diffs):
            diff = self.diffs[which]
            utils.write(filename, self.header + '\n' + diff + '\n')
            return True
        else:
            return False

    def diffs(self):
        """Returns the list of diffs."""
        return self._diffs

    def diff_subset(self, diff, start, end):
        """Processes the diffs and returns a selected subset from that diff.
        """
        adds = 0
        deletes = 0
        newdiff = []
        local_offset = 0
        offset = self._diff_spans[diff][0]
        diffguts = '\n'.join(self._diffs[diff])

        for line in self._diffs[diff]:
            line_start = offset + local_offset
            local_offset += len(line) + 1 #\n
            line_end = offset + local_offset
            # |line1 |line2 |line3 |
            #   |--selection--|
            #   '-start       '-end
            # selection has head of diff (line3)
            if start < line_start and end > line_start and end < line_end:
                newdiff.append(line)
                if line.startswith('+'):
                    adds += 1
                if line.startswith('-'):
                    deletes += 1
            # selection has all of diff (line2)
            elif start <= line_start and end >= line_end:
                newdiff.append(line)
                if line.startswith('+'):
                    adds += 1
                if line.startswith('-'):
                    deletes += 1
            # selection has tail of diff (line1)
            elif start >= line_start and start < line_end - 1:
                newdiff.append(line)
                if line.startswith('+'):
                    adds += 1
                if line.startswith('-'):
                    deletes += 1
            else:
                # Don't add new lines unless selected
                if line.startswith('+'):
                    continue
                elif line.startswith('-'):
                    # Don't remove lines unless selected
                    newdiff.append(' ' + line[1:])
                else:
                    newdiff.append(line)

        new_count = self._headers[diff][1] + adds - deletes
        if new_count != self._headers[diff][3]:
            header = '@@ -%d,%d +%d,%d @@' % (
                            self._headers[diff][0],
                            self._headers[diff][1],
                            self._headers[diff][2],
                            new_count)
            newdiff[0] = header

        return (self.header + '\n' + '\n'.join(newdiff) + '\n')

    def spans(self):
        """Returns the line spans of each hunk."""
        return self._diff_spans

    def offsets(self):
        """Returns the offsets."""
        return self._diff_offsets

    def set_diff_to_offset(self, offset):
        """Sets the diff selection to be the hunk at a particular offset."""
        self.offset = offset
        self.diffs, self.selected = self.diff_for_offset(offset)

    def set_diffs_to_range(self, start, end):
        """Sets the diff selection to be a range of hunks."""
        self.start = start
        self.end = end
        self.diffs, self.selected = self.diffs_for_range(start,end)

    def diff_for_offset(self, offset):
        """Returns the hunks for a particular offset."""
        for idx, diff_offset in enumerate(self._diff_offsets):
            if offset < diff_offset:
                return (['\n'.join(self._diffs[idx])], [idx])
        return ([],[])

    def diffs_for_range(self, start, end):
        """Returns the hunks for a selected range."""
        diffs = []
        indices = []
        for idx, span in enumerate(self._diff_spans):
            has_end_of_diff = start >= span[0] and start < span[1]
            has_all_of_diff = start <= span[0] and end >= span[1]
            has_head_of_diff = end >= span[0] and end <= span[1]

            selected_diff =(has_end_of_diff
                    or has_all_of_diff
                    or has_head_of_diff)
            if selected_diff:
                diff = '\n'.join(self._diffs[idx])
                diffs.append(diff)
                indices.append(idx)
        return diffs, indices

    def parse_diff(self, diff):
        """Parses a diff and extracts headers, offsets, hunks, etc.
        """
        total_offset = 0
        self._idx = -1
        self._headers = []

        for idx, line in enumerate(diff.split('\n')):
            match = self._header_re.match(line)
            if match:
                self._headers.append([
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                        int(match.group(4))
                        ])
                self._diffs.append( [line] )

                line_len = len(line) + 1 #\n
                self._diff_spans.append([total_offset,
                        total_offset + line_len])
                total_offset += line_len
                self._diff_offsets.append(total_offset)
                self._idx += 1
            else:
                if self._idx < 0:
                    errmsg = 'Malformed diff?\n\n%s' % diff
                    raise AssertionError, errmsg
                line_len = len(line) + 1
                total_offset += line_len

                self._diffs[self._idx].append(line)
                self._diff_spans[-1][-1] += line_len
                self._diff_offsets[self._idx] += line_len

    def process_diff_selection(self, selected, offset, selection,
                               apply_to_worktree=False):
        """Processes a diff selection and applies changes to git."""
        if selection:
            # qt destroys \r\n and makes it \n with no way of going back.
            # boo!  we work around that here.
            # I think this was win32-specific.  We might want to do
            # this on win32 only (TODO verify)
            if selection not in self.fwd_diff:
                special_selection = selection.replace('\n', '\r\n')
                if special_selection in self.fwd_diff:
                    selection = special_selection
                else:
                    return
            start = self.fwd_diff.index(selection)
            end = start + len(selection)
            self.set_diffs_to_range(start, end)
        else:
            self.set_diff_to_offset(offset)
            selected = False
        # Process diff selection only
        if selected:
            for idx in self.selected:
                contents = self.diff_subset(idx, start, end)
                if contents:
                    tmpfile = self.model.tmp_filename()
                    utils.write(tmpfile, contents)
                    if apply_to_worktree:
                        self.model.apply_diff_to_worktree(tmpfile)
                    else:
                        self.model.apply_diff(tmpfile)
                    os.unlink(tmpfile)
        # Process a complete hunk
        else:
            for idx, diff in enumerate(self.diffs):
                tmpfile = self.model.tmp_filename()
                if self.write_diff(tmpfile,idx):
                    if apply_to_worktree:
                        self.model.apply_diff_to_worktree(tmpfile)
                    else:
                        self.model.apply_diff(tmpfile)
                    os.unlink(tmpfile)
