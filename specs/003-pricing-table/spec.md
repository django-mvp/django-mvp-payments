# Feature Specification: Offer plans through the provider's own pricing table

**Feature Branch**: `003-pricing-table`

**Created**: 2026-09-22

**Status**: Replaced by specification 005

**Serves**: G1, G2

**Roadmap**: R2 — The first backend: the package's own Stripe app

**Issue**: #24

The plans page this specification described rendered Stripe's own pricing table. That page no
longer exists. The plans are now drawn by the package from the project's Stripe catalogue and
bought through a checkout the Stripe app starts, as `specs/005-plans-drawn-here/spec.md`
specifies, and [ADR 0013](../../docs/adr/0013-the-plans-are-drawn-from-a-cached-catalogue.md)
records why. Everything this specification required of the plans page, the pricing table
component and its settings is superseded there.

One requirement from this specification is not about the plans page and still holds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A subscriber switches plans at the provider (Priority: P2)

A current subscriber opens their user subscriptions page and follows its way to another plan. They
reach Stripe's own plan-change screen. A person with no current subscription is led to the plans
page instead.

**Independent Test**: As a subscriber, use the way to another plan and confirm it leads to Stripe's
plan-change screen. As someone with no subscription, confirm it leads to the plans page.

**Acceptance Scenarios**:

1. **Given** a person with one current subscription, **When** they use the way to another plan,
   **Then** they reach Stripe's plan-change screen for that subscription.
2. **Given** a person with several current subscriptions, **When** they use it, **Then** they reach
   the portal's home.
3. **Given** a person with no current subscription, **When** the user subscriptions page renders,
   **Then** its way to another plan leads to the plans page, when the project has mounted it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-015**: The user subscriptions page's way to another plan MUST, for a current subscriber, lead
  to the provider's own plan-change screen through the Stripe app's plan-switch view: for their
  subscription when they hold one, and for the portal's home when they hold several. A person with
  no current subscription MUST be led to the plans page.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A subscriber reaches Stripe's plan-change screen from the user subscriptions page
  without any page of the project's own.
