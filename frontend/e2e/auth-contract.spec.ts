import { test, expect, Page } from '@playwright/test';

const token = `e30.${btoa(JSON.stringify({ user_id: 1, first_name: 'Test', last_name: 'User', email: 'test@example.com' }))}.signature`;

async function harness(page: Page) {
  await page.route(url => url.pathname.startsWith('/api/'), route => route.fulfill({ status: 403, json: { error: 'No session' } }));
  await page.goto('/auth/sign-in');
  await page.evaluate(async () => {
    const modulePath = '/e2e/auth-harness.tsx';
    const module = await import(modulePath);
    module.mountAuthHarness();
  });
  await expect(page.getByRole('button', { name: 'Register', exact: true })).toBeVisible();
}

for (const status of [201, 202, 204]) {
  test(`SignUp accepts HTTP ${status}`, async ({ page }) => {
    await harness(page);
    await page.route('**/api/register/', route => route.fulfill({
      status, ...(status === 204 ? {} : { json: { message: 'Created' } }),
    }));
    await page.getByRole('button', { name: 'Register', exact: true }).click();
    await expect(page.locator('#auth-result')).toHaveText('registered');
  });
}

for (const status of [204, 503]) {
  test(`SignOut calls logout and clears state/cache when server returns ${status}`, async ({ page }) => {
    await harness(page);
    await page.route('**/api/token/', route => route.fulfill({ json: { access: token } }));
    await page.route('**/api/logout/', route => route.fulfill({ status }));
    await page.getByRole('button', { name: 'Login', exact: true }).click();
    await expect(page.locator('#auth-user')).toHaveText('test@example.com');
    await expect(page.locator('#auth-cache')).toHaveText('cached');
    const logout = page.waitForRequest('**/api/logout/');
    await page.getByRole('button', { name: 'Logout', exact: true }).click();
    expect((await logout).method()).toBe('POST');
    await expect(page.locator('#auth-user')).toHaveText('anonymous');
    await expect(page.locator('#auth-tokens')).toHaveText('null');
    await expect(page.locator('#auth-cache')).toHaveText('empty');
  });
}

test('refresh uses only the cookie and access_token response', async ({ page }) => {
  await harness(page);
  await page.route('**/api/token/refresh/', route => route.fulfill({ json: { access_token: token } }));
  const request = page.waitForRequest('**/api/token/refresh/');
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  expect((await request).postDataJSON()).toEqual({});
  await expect(page.locator('#auth-result')).toHaveText('refreshed');
  await expect(page.locator('#auth-user')).toHaveText('test@example.com');
  await expect(page.locator('#auth-tokens')).toHaveText(JSON.stringify({ access: token }));
});

test('registration displays the error message from the server', async ({ page }) => {
  await page.route('**/api/register/', route => route.fulfill({ status: 400, json: { message: 'Email này đã được sử dụng.' } }));
  await page.goto('/auth/sign-up');
  const inputs = page.locator('form input');
  for (const [index, value] of ['Test', 'User', 'test@example.com', 'TestPassword123!', 'TestPassword123!'].entries()) {
    await inputs.nth(index).fill(value);
  }
  await page.locator('form button[type="submit"]').click();
  await expect(page.getByText('Email này đã được sử dụng.', { exact: true })).toBeVisible();
});

test('a refresh finishing after logout cannot restore the user', async ({ page }) => {
  await harness(page);
  let release: () => void = () => {};
  const released = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/token/refresh/', async route => {
    await released;
    await route.fulfill({ json: { access_token: token } });
  });
  await page.route('**/api/logout/', route => route.fulfill({ status: 204 }));
  const request = page.waitForRequest('**/api/token/refresh/');
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await request;
  await page.getByRole('button', { name: 'Logout', exact: true }).click();
  await expect(page.locator('#auth-user')).toHaveText('anonymous');
  release();
  await expect(page.locator('#auth-result')).toHaveText('refresh failed');
  await expect(page.locator('#auth-user')).toHaveText('anonymous');
});
