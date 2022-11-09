from bgo.shell_commands import Command


class Year(Command):

    keywords = ['year']
    help_text = """{keyword}
{divider}
Summary: Limits the search results to a date range.

Usage: {keyword} <min_year> <max_year>

No argument clears the limits.
One argument sets the minimum year with no maximum.
Two arguments sets a range of years.

Examples:

    {keyword}
    {keyword} 2019
    {keyword} 2000 2010

"""

    def do_command(self, *args):
        orig_min = self.state.min_year
        orig_max = self.state.max_year
        try:
            if not args:
                self.state.min_year = None
                self.state.max_year = None
                print('Limits cleared.')
                return
            elif len(args) == 1:
                self.state.min_year = int(args[0])
                self.state.max_year = None
                print(f'Limiting results to year {self.state.min_year} and newer.')
            elif len(args) == 2:
                self.state.min_year = int(args[0])
                self.state.max_year = int(args[1])
                print(f'Limiting results between years {self.state.min_year} and {self.state.max_year}.')
            else:
                print(f'Unknown number of arguments.')
        except (ValueError, TypeError):
            print('Invalid arguments.')
            self.state.min_year = orig_min
            self.state.max_year = orig_max
            return



