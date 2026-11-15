import { test, expect } from '@playwright/test';

test.describe('GigBid Onboarding', () => {
  test('sign in and redirect to job inbox', async ({ page }) => {
    await page.goto('/');
    
    // Fill name
    await page.fill('input[placeholder="Your name"]', 'Test User');
    
    // Select persona
    await page.selectOption('select', 'AI/ML Engineer');
    
    // Click enter
    await page.click('text=Enter GigBid');
    
    // Should redirect to jobs
    await expect(page).toHaveURL(/.*\/jobs/);
    await expect(page.locator('h2')).toContainText('Job Inbox');
  });

  test('sign out returns to sign in page', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[placeholder="Your name"]', 'Test User');
    await page.selectOption('select', 'AI/ML Engineer');
    await page.click('text=Enter GigBid');
    
    // Sign out
    await page.click('text=Sign Out');
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1')).toContainText('GigBid');
  });
});