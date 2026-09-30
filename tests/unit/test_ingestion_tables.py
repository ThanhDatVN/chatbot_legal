from ingestion.tables import LEFT, UP, TableBlock, column_labels, header_row_count, is_real_table, \
    resolve_document_tables


def block(raw, dirs=None, page=1):
    dirs = dirs or [[(UP if v is None else None) for v in row] for row in raw]
    return TableBlock(bbox=(0, 0, 100, 100), col_count=len(raw[0]), row_count=len(raw), raw=raw, merge_dir=dirs,
                      page=page)


def test_fake_table_from_paragraph_is_rejected():
    rows = [["a)", "Thành lập cơ sở giáo dục nghề nghiệp", None], ["làm việc để đào tạo", None, None],
            ["người lao động; phối hợp", None, None]]
    assert not is_real_table(rows)


def test_header_rows_stop_at_first_numeric_row():
    rows = [["Vùng", "Mức lương tháng", "Mức lương giờ"], ["Vùng I", "5.310.000", "25.500"]]
    assert header_row_count(rows) == 1


def test_column_labels_distinguish_horizontal_and_vertical_merges():
    header = [["Lao động nam", None, None], ["Thời điểm sinh", None, "Tuổi nghỉ hưu"], ["Tháng", "Năm", None]]
    dirs = [[None, LEFT, LEFT], [None, LEFT, None], [None, None, UP]]
    assert column_labels(header, dirs) == ["Lao động nam – Thời điểm sinh – Tháng",
                                           "Lao động nam – Thời điểm sinh – Năm",
                                           "Lao động nam – Tuổi nghỉ hưu"]


def test_rows_become_labelled_text():
    t = block([["Vùng", "Mức lương tháng"], ["Vùng I", "5.310.000"], ["Vùng II", "4.730.000"]])
    resolve_document_tables([t])
    assert t.rows_text == ["Vùng: Vùng I; Mức lương tháng: 5.310.000", "Vùng: Vùng II; Mức lương tháng: 4.730.000"]


def test_vertical_merge_straddling_a_page_break_is_joined():
    p1 = block([["Năm", "Tuổi"], ["2021", "60 tuổi"], ["2022", None]], page=1)
    p2 = block([["2023", ""], ["2024", None]], page=2)  # merged cell continues on the next page with no text
    resolve_document_tables([p1, p2])
    assert p2.header_source == "continued"
    assert p2.rows_text == ["Năm: 2023; Tuổi: 60 tuổi", "Năm: 2024; Tuổi: 60 tuổi"]


def test_narrower_continuation_maps_to_last_column_group():
    header = [["Lao động nam", None, "Lao động nữ", None], ["Năm", "Tuổi", "Năm", "Tuổi"]]
    dirs = [[None, LEFT, None, LEFT], [None, None, None, None]]
    wide = block(header + [["2021", "60 tuổi", "2021", "55 tuổi"]],
                 dirs + [[None, None, None, None]], page=1)
    narrow = block([["2031", "58 tuổi"]], page=2)
    resolve_document_tables([wide, narrow])
    assert narrow.header_source == "continued_group"
    assert narrow.rows_text == ["Lao động nữ – Năm: 2031; Lao động nữ – Tuổi: 58 tuổi"]
