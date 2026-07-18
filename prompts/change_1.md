You are a senior Full-Stack Engineer, UI/UX Designer, and Product Manager. Review the existing frontend application part and implement the following tasks while maintaining the current architecture, coding standards, and design consistency.

## Task 1: Authentication Flow

Implement a complete authentication system.

### Requirements

* When the frontend loads, users should be presented with an authentication experience before accessing the application.
* Create:

  * Login page
  * Signup page
* Authentication flow should:

  * Validate user input.
  * Handle loading and error states.
  * Persist authenticated sessions appropriately.
  * Redirect authenticated users to the dashboard.
  * Prevent unauthenticated users from accessing protected routes.
* If authentication already exists, review it and improve it rather than rebuilding unnecessarily.
* Ensure the UI is modern, responsive, and consistent with the application's design language.

---

## Task 2: Branding

I have already provided the MAQ logo in the project assets. names as MAQ_dp.webpg file

Please:

* Locate the logo.
* Add it to the navigation bar.
* Ensure:

  * Proper sizing
  * High-resolution rendering
  * Good spacing
  * Responsive behavior
  * Appropriate alignment with navigation items
* Follow modern UI/UX best practices.

---

## Task 3: KPI & Dashboard Review

Review the dashboard from the perspective of a **Retailer/Supplier**.

Evaluate every KPI currently displayed and answer the following:

1. Does this KPI help a retailer make better business decisions?
2. Does it directly impact:

   * Profitability
   * Inventory optimization
   * Supply chain efficiency
   * Sales growth
   * Customer service
3. Is it actionable?
4. Would a retailer actually look at this every day?
5. Is it redundant or low-value?

After reviewing:

### Produce a report containing:

#### Current KPI Analysis

For each KPI:

* Purpose
* Business value
* Strengths
* Weaknesses
* Keep / Modify / Remove recommendation

#### Missing KPIs

Suggest additional KPIs that would create more value, such as:

* Revenue
* Gross Margin
* Net Margin
* Inventory Turnover
* Days of Inventory
* Fill Rate
* Stockout Rate
* Backorders
* Supplier Performance
* Purchase Order Status
* On-Time Delivery
* Average Order Value
* Sell-through Rate
* Dead Stock
* Slow-moving Inventory
* Demand Forecast Accuracy
* Customer Retention
* Profit by Product Category
* ABC Inventory Classification
* Top/Bottom Performing SKUs
* Cash Flow Indicators

Also recommend:

* Better charts
* Better layouts
* Better data hierarchy
* Better visualizations
* Better color usage
* Better information density
* Better mobile responsiveness

---

## Implementation Policy

Do **not** implement any KPI or UI changes immediately.

Instead:

1. Analyze the existing dashboard.
2. Produce a detailed improvement report.
3. Explain the reasoning behind every recommendation.
4. Wait for my approval.

Only after I explicitly approve the recommendations should you implement the proposed dashboard and KPI improvements.

---

## Code Quality Requirements

* Follow clean architecture principles.
* Avoid unnecessary code duplication.
* Reuse existing components wherever possible.
* Ensure responsive design.
* Preserve the current styling unless improvements are justified.
* Do not break existing functionality.
* Document any architectural decisions made during implementation.

Begin with the authentication and branding tasks. Perform the KPI review in parallel, but do not implement dashboard changes until I grant permission.
