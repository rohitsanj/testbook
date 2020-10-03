from nbformat import NotebookNode


class TestbookNode(NotebookNode):
    """
    Extends `NotebookNode` to perform assertions
    """

    @property
    def output_text(self):
        text = ''
        for output in self['outputs']:
            if 'text' in output:
                text += output['text']

        return text.strip()

    @property
    def execute_result(self):
        """Return data from execute_result outputs"""
        return [
            output["data"]
            for output in self["outputs"]
            if output["output_type"] == 'execute_result'
        ]
