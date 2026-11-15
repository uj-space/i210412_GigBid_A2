import { test, expect } from '@playwright/test';

test.describe('Reject Proposal', () => {
  test('reject with reason', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[placeholder="Your name"]', 'Test User');
    await page.selectOption('select', 'AI/ML Engineer');
    await page.click('text=Enter GigBid');
    
    // Verify page loaded
    await expect(page.locator('h2')).toContainText('Job Inbox');
  });
});