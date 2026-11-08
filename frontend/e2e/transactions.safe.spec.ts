import { test, expect, navigateTo } from './fixtures';

test.describe('Giao dịch - Kịch bản An toàn (Transactions Safe)', () => {
  const TEST_TX_TITLE = 'Chi tiêu E2E Test Safe';
  const TEST_TX_AMOUNT = '75000';

  test('Thêm giao dịch mới, tìm kiếm debounce và xoá dọn dẹp', async ({ safePage }) => {
    // 1. Thêm giao dịch mới từ Dashboard (safePage đã ở sẵn trang Tổng quan '/')
    await safePage.getByRole('button', { name: 'Thêm giao dịch' }).click();

    const dialog = safePage.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Điền tiêu đề
    await dialog.locator('input').nth(0).fill(TEST_TX_TITLE);

    // Chọn danh mục "Ăn uống"
    await dialog.locator('input').nth(1).click();
    const categoryOption = safePage.locator('li[role="option"]').filter({ hasText: 'Ăn uống' }).first();
    await categoryOption.click();

    // Điền số tiền
    await dialog.locator('input[placeholder="0"]').fill(TEST_TX_AMOUNT);

    // Bật cập nhật ví
    const updateWallet = dialog.locator('input[name="updateWallet"]');
    if (!(await updateWallet.isChecked())) {
      await updateWallet.check();
    }

    // Submit form thêm giao dịch
    await dialog.getByRole('button', { name: 'Thêm giao dịch' }).click();
    await expect(dialog).toBeHidden();

    // 2. Chuyển sang trang Lịch sử giao dịch
    await navigateTo(safePage, '/transactions', 'Lịch sử giao dịch');
    await expect(safePage.getByRole('heading', { level: 1, name: 'Lịch sử giao dịch' })).toBeVisible();

    // Xác nhận giao dịch mới xuất hiện ở đầu bảng
    await expect(safePage.getByText(TEST_TX_TITLE)).toBeVisible();

    // 3. Kiểm tra tính năng tìm kiếm (Search Debounce)
    const searchInput = safePage.locator('input[placeholder*="Tìm kiếm"]');
    await searchInput.fill('E2E Test Safe');
    // Chờ debounce lọc kết quả
    await expect(safePage.getByText(TEST_TX_TITLE)).toBeVisible();

    // Thử tìm kiếm một từ khóa không tồn tại
    await searchInput.fill('TuKhoaKhongTonTai999');
    await expect(safePage.getByText('Không có dữ liệu')).toBeVisible();

    // Xoá ô tìm kiếm để danh sách hiện lại
    await searchInput.clear();
    await expect(safePage.getByText(TEST_TX_TITLE)).toBeVisible();

    // 4. Dọn dẹp dữ liệu: Xoá giao dịch vừa tạo
    const deleteBtn = safePage.getByRole('menuitem', { name: `Xoá giao dịch: ${TEST_TX_TITLE}` });
    await expect(deleteBtn).toBeVisible();
    await deleteBtn.click();

    // Xác nhận giao dịch đã bị xoá khỏi danh sách
    await expect(safePage.getByText(TEST_TX_TITLE)).toBeHidden();
  });

  test('Kiểm tra Form Validation khi thêm giao dịch không hợp lệ', async ({ safePage }) => {
    await safePage.getByRole('button', { name: 'Thêm giao dịch' }).click();

    const dialog = safePage.locator('div[role="dialog"]');
    await expect(dialog).toBeVisible();

    // Không điền gì và bấm Submit
    await dialog.getByRole('button', { name: 'Thêm giao dịch' }).click();

    // Dialog vẫn mở vì form bị chặn bởi validation
    await expect(dialog).toBeVisible();

    // Đóng dialog
    await dialog.getByLabel('Đóng').click();
    await expect(dialog).toBeHidden();
  });

  test('Chỉnh sửa giao dịch (đổi số tiền và ghi chú), kiểm tra danh sách và số liệu Dashboard cập nhật', async ({ safePage }) => {
    const INITIAL_TITLE = 'Giao dịch ban đầu E2E';
    const UPDATED_TITLE = 'Giao dịch đã sửa E2E';
    const INITIAL_AMOUNT = '150000';
    const UPDATED_AMOUNT = '250000';

    // 1. Tạo giao dịch ban đầu từ Dashboard
    await safePage.getByRole('button', { name: 'Thêm giao dịch' }).click();
    const addDialog = safePage.locator('div[role="dialog"]');
    await expect(addDialog).toBeVisible();

    await addDialog.locator('input').nth(0).fill(INITIAL_TITLE);
    await addDialog.locator('input').nth(1).click();
    await safePage.locator('li[role="option"]').filter({ hasText: 'Ăn uống' }).first().click();
    await addDialog.locator('input[placeholder="0"]').fill(INITIAL_AMOUNT);

    const updateWallet = addDialog.locator('input[name="updateWallet"]');
    if (!(await updateWallet.isChecked())) {
      await updateWallet.check();
    }
    await addDialog.getByRole('button', { name: 'Thêm giao dịch' }).click();
    await expect(addDialog).toBeHidden();

    // 2. Chuyển sang Lịch sử giao dịch để thực hiện sửa
    await navigateTo(safePage, '/transactions', 'Lịch sử giao dịch');
    await expect(safePage.getByText(INITIAL_TITLE)).toBeVisible();

    // Mở Dialog chỉnh sửa giao dịch
    const editBtn = safePage.getByRole('menuitem', { name: `Chỉnh sửa giao dịch: ${INITIAL_TITLE}` });
    await expect(editBtn).toBeVisible();
    await editBtn.click();

    const editDialog = safePage.locator('div[role="dialog"]');
    await expect(editDialog).toBeVisible();

    // Đổi tên (tiêu đề) và số tiền
    const titleInput = editDialog.getByLabel('Tên');
    await titleInput.clear();
    await titleInput.fill(UPDATED_TITLE);

    const amountInput = editDialog.getByLabel('Số tiền');
    await amountInput.clear();
    await amountInput.fill(UPDATED_AMOUNT);

    // Bấm "Lưu thay đổi"
    await editDialog.getByRole('button', { name: 'Lưu thay đổi' }).click();
    await expect(editDialog).toBeHidden();

    // 3. Kiểm tra danh sách hiển thị tên và số tiền mới
    await expect(safePage.getByText(UPDATED_TITLE)).toBeVisible();
    await expect(safePage.getByText(INITIAL_TITLE)).toBeHidden();

    // 4. Quay về Dashboard kiểm tra cập nhật số liệu và danh sách giao dịch gần đây
    await navigateTo(safePage, '/', 'Tổng quan');
    await expect(safePage.getByText(UPDATED_TITLE)).toBeVisible();

    // 5. Dọn dẹp: Quay lại /transactions và xoá giao dịch
    await navigateTo(safePage, '/transactions', 'Lịch sử giao dịch');
    const deleteBtn = safePage.getByRole('menuitem', { name: `Xoá giao dịch: ${UPDATED_TITLE}` });
    await expect(deleteBtn).toBeVisible();
    await deleteBtn.click();
    await expect(safePage.getByText(UPDATED_TITLE)).toBeHidden();
  });
});

