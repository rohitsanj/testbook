import inspect
import json
import textwrap
from collections.abc import Callable

from nbformat.v4 import new_code_cell

from nbclient import NotebookClient
from testbook.testbooknode import TestbookNode
from testbook.exceptions import CellTagNotFoundError


class TestbookNotebookClient(NotebookClient):
    @staticmethod
    def _execute_result(outputs):
        """Return data from execute_result outputs"""

        if outputs is None:
            return

        return [output["data"] for output in outputs if output.output_type == 'execute_result']

    def _get_cell_index(self, tag):
        """Get cell index from the cell tag"""
        if isinstance(tag, int):
            return tag
        elif not isinstance(tag, str):
            raise TypeError('expected tag as str')

        for idx, cell in enumerate(self.nb['cells']):
            metadata = cell['metadata']
            if "tags" in metadata and tag in metadata['tags']:
                return idx

        raise CellTagNotFoundError("Cell tag '{}' not found".format(tag))

    def execute_cell(self, cell, **kwargs):
        """Executes a cell or list of cells

        Parameters
        ----------
            cell : int or str
                cell index (or cell tag)

        Returns
        -------
            executed_cells : dict or list
        """
        if not isinstance(cell, list):
            cell = [cell]

        cell_indexes = cell

        if all(isinstance(x, str) for x in cell):
            cell_indexes = [self._get_cell_index(tag) for tag in cell]

        executed_cells = []
        for idx in cell_indexes:
            cell = super().execute_cell(self.nb['cells'][idx], idx, **kwargs)
            executed_cells.append(cell)

        return executed_cells[0] if len(executed_cells) == 1 else executed_cells

    def cell_output_text(self, cell):
        """Return cell text output

        Parameters
        ----------
            cell : int or str
                cell index (or cell tag)

        Returns
        -------
            text : str
        """
        cell_index = cell
        if isinstance(cell, str):
            # Get cell index of cell tag
            cell_index = self._get_cell_index(cell)
        text = ''
        outputs = self.nb['cells'][cell_index]['outputs']
        for output in outputs:
            if 'text' in output:
                text += output['text']

        return text.strip()

    def inject(self, code, args=None, prerun=None):
        """Injects code into the notebook and executes it

        Parameters
        ----------
            code :  str or Callable
                Code or function to be injected
            args : tuple (optional)
                Tuple of arguments to be passed to the function
            prerun : list (optional)
                List of cells to be pre-run prior to injection
        Returns
        -------
            cell : TestbookNode
        """
        if isinstance(code, str):
            lines = textwrap.dedent(code)
        elif isinstance(code, Callable):
            func = code
            lines = inspect.getsource(func)
            args_str = ', '.join(map(json.dumps, args)) if args else ''

            # Add the function call to the same cell
            lines += textwrap.dedent(
                f"""
                # Calling {func.__name__}
                {func.__name__}({args_str})
            """
            )
        else:
            raise TypeError('can only inject function or code block as str')

        # Execute the pre-run cells if passed
        if prerun is not None:
            self.execute_cell(prerun)

        # Create a code cell
        inject_cell = new_code_cell(lines)

    def value(self, name):
        """Extract a JSON-able variable value from notebook kernel"""

        result = self.inject(name)
        if not self._execute_result(result.outputs):
            raise ValueError('code provided does not produce execute_result')

        code = """
        from IPython.display import JSON
        JSON({"value" : _})
        """
        cell = self.inject(code)
        return cell.outputs[0].data['application/json']['value']
