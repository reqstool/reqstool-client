# Copyright © LFV

from reqstool.lsp.annotation_parser import annotation_at_position, find_all_annotations, is_inside_annotation


# -- find_all_annotations: Python/Java (source annotations) --


def test_python_single_requirement():
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    result = find_all_annotations(text, "python")
    assert len(result) == 1
    assert result[0].kind == "Requirements"
    assert result[0].raw_id == "REQ_010"
    assert result[0].line == 0


def test_python_multiple_requirements():
    text = '@Requirements("REQ_010", "REQ_011")\ndef foo(): pass'
    result = find_all_annotations(text, "python")
    assert len(result) == 2
    assert result[0].raw_id == "REQ_010"
    assert result[1].raw_id == "REQ_011"


def test_python_svcs():
    text = '@SVCs("SVC_010")\ndef test_foo(): pass'
    result = find_all_annotations(text, "python")
    assert len(result) == 1
    assert result[0].kind == "SVCs"
    assert result[0].raw_id == "SVC_010"


def test_python_urn_prefixed_id():
    text = '@Requirements("ms-001:REQ_010")\ndef foo(): pass'
    result = find_all_annotations(text, "python")
    assert len(result) == 1
    assert result[0].raw_id == "ms-001:REQ_010"


def test_python_multiline_annotation():
    text = '@Requirements(\n    "REQ_010",\n    "REQ_011"\n)\ndef foo(): pass'
    result = find_all_annotations(text, "python")
    assert len(result) == 2
    assert result[0].raw_id == "REQ_010"
    assert result[0].line == 1
    assert result[1].raw_id == "REQ_011"
    assert result[1].line == 2


def test_python_no_annotations():
    text = "def foo(): pass\nx = 42"
    result = find_all_annotations(text, "python")
    assert result == []


def test_python_multiple_annotations_in_file():
    text = '@Requirements("REQ_010")\ndef foo(): pass\n\n@SVCs("SVC_010")\ndef test_foo(): pass'
    result = find_all_annotations(text, "python")
    assert len(result) == 2
    assert result[0].kind == "Requirements"
    assert result[1].kind == "SVCs"


def test_python_column_positions():
    text = '@Requirements("REQ_010")'
    result = find_all_annotations(text, "python")
    assert len(result) == 1
    # @Requirements("REQ_010") — R is at col 15 (0-indexed)
    assert result[0].start_col == 15
    assert result[0].end_col == 22


def test_java_single_requirement():
    text = '@Requirements("REQ_010")\npublic void foo() {}'
    result = find_all_annotations(text, "java")
    assert len(result) == 1
    assert result[0].kind == "Requirements"
    assert result[0].raw_id == "REQ_010"


def test_java_multiple_requirements():
    text = '@Requirements("REQ_010", "REQ_011")\npublic void foo() {}'
    result = find_all_annotations(text, "java")
    assert len(result) == 2


# -- find_all_annotations: JSDoc (TypeScript/JavaScript) --


def test_jsdoc_single_requirement():
    text = "/** @Requirements REQ_010 */\nfunction foo() {}"
    result = find_all_annotations(text, "typescript")
    assert len(result) == 1
    assert result[0].kind == "Requirements"
    assert result[0].raw_id == "REQ_010"
    assert result[0].line == 0


def test_jsdoc_multiple_requirements():
    text = "/** @Requirements REQ_010, REQ_011 */\nfunction foo() {}"
    result = find_all_annotations(text, "typescript")
    assert len(result) == 2
    assert result[0].raw_id == "REQ_010"
    assert result[1].raw_id == "REQ_011"


def test_jsdoc_svcs():
    text = '/** @SVCs SVC_010 */\ntest("foo", () => {});'
    result = find_all_annotations(text, "javascript")
    assert len(result) == 1
    assert result[0].kind == "SVCs"
    assert result[0].raw_id == "SVC_010"


def test_jsdoc_urn_prefixed_id():
    text = "/** @Requirements ms-001:REQ_010 */"
    result = find_all_annotations(text, "typescript")
    assert len(result) == 1
    assert result[0].raw_id == "ms-001:REQ_010"


def test_jsdoc_no_annotations():
    text = "function foo() {}\nconst x = 42;"
    result = find_all_annotations(text, "typescript")
    assert result == []


def test_jsdoc_column_positions():
    text = "/** @Requirements REQ_010 */"
    result = find_all_annotations(text, "typescript")
    assert len(result) == 1
    assert result[0].start_col == 18
    assert result[0].end_col == 25


def test_jsdoc_javascriptreact():
    text = "/** @Requirements REQ_010 */"
    result = find_all_annotations(text, "javascriptreact")
    assert len(result) == 1


def test_jsdoc_typescriptreact():
    text = "/** @SVCs SVC_001 */"
    result = find_all_annotations(text, "typescriptreact")
    assert len(result) == 1


# -- annotation_at_position --


def test_position_cursor_on_id():
    text = '@Requirements("REQ_010")'
    match = annotation_at_position(text, 0, 17, "python")
    assert match is not None
    assert match.raw_id == "REQ_010"


def test_position_cursor_outside_id():
    text = '@Requirements("REQ_010")'
    match = annotation_at_position(text, 0, 5, "python")
    assert match is None


def test_position_cursor_on_second_id():
    text = '@Requirements("REQ_010", "REQ_011")'
    match = annotation_at_position(text, 0, 27, "python")
    assert match is not None
    assert match.raw_id == "REQ_011"


def test_position_wrong_line():
    text = '@Requirements("REQ_010")\ndef foo(): pass'
    match = annotation_at_position(text, 1, 5, "python")
    assert match is None


def test_position_jsdoc_cursor_on_id():
    text = "/** @Requirements REQ_010 */"
    match = annotation_at_position(text, 0, 20, "typescript")
    assert match is not None
    assert match.raw_id == "REQ_010"


# -- is_inside_annotation --


def test_inside_requirements_quotes():
    line = '@Requirements("REQ_")'
    result = is_inside_annotation(line, 17, "python")
    assert result == "Requirements"


def test_inside_svcs_quotes():
    line = '@SVCs("SVC_")'
    result = is_inside_annotation(line, 8, "python")
    assert result == "SVCs"


def test_inside_outside_annotation():
    line = "def foo(): pass"
    result = is_inside_annotation(line, 5, "python")
    assert result is None


def test_inside_before_paren():
    line = '@Requirements("REQ_010")'
    result = is_inside_annotation(line, 5, "python")
    assert result is None


def test_inside_jsdoc():
    line = "/** @Requirements REQ_ */"
    result = is_inside_annotation(line, 20, "typescript")
    assert result == "Requirements"


def test_inside_jsdoc_outside():
    line = "const x = 42;"
    result = is_inside_annotation(line, 5, "typescript")
    assert result is None


def test_inside_open_paren_multiline():
    line = '@Requirements("REQ_010",'
    result = is_inside_annotation(line, 20, "python")
    assert result == "Requirements"


# -- Unsupported language --


def test_unknown_language_find():
    text = '@Requirements("REQ_010")'
    result = find_all_annotations(text, "rust")
    assert result == []


def test_unknown_language_position():
    text = '@Requirements("REQ_010")'
    result = annotation_at_position(text, 0, 17, "rust")
    assert result is None


def test_unknown_language_inside():
    line = '@Requirements("REQ_")'
    result = is_inside_annotation(line, 17, "rust")
    assert result is None
