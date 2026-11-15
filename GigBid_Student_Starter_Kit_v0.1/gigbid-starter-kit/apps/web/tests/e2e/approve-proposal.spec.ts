import { test, expect } from '@playwright/test';

test.describe('Proposal Approval', () => {
  test('approve proposal from job detail', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[placeholder="Your name"]', 'Test User');
    await page.selectOption('select', 'AI/ML Engineer');
    await page.click('text=Enter GigBid');
    
    // Click a job
    await page.click('text=Build churn prediction model');
    
    // Should show job detail
    await expect(page.locator('h2')).toContainText('Job Detail');
  });
});