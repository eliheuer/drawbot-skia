size(520, 360)

for page in range(3):
    if page:
        newPage(520, 360)
    fill(0.96)
    rect(0, 0, width(), height())
    fill(0.12, 0.2, 0.32)
    fontSize(96)
    text(str(page + 1), (56, 188))
    fill(0.92, 0.35, 0.14)
    oval(246 + page * 16, 116, 128, 128)
    fill(0.08)
    fontSize(19)
    text(f"page {page + 1} of {pageCount()}", (56, 62))
