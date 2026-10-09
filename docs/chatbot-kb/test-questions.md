# Chatbot Test Questions

Topic: Questions with expected answers used to check the ToyBox shopper assistant.
Source: The knowledge base documents listed on each entry.

## Q: How much is shipping?
Expected: $5.99 flat; free when subtotal is $50.00 or more.
Source: 05-shipping-tax-pricing.md

## Q: How much tax will I pay?
Expected: 6.63% of the subtotal only; shipping is not taxed.
Source: 05-shipping-tax-pricing.md

## Q: What is the total for a $30.00 order?
Expected: $37.98 ($30.00 + $5.99 shipping + $1.99 tax).
Source: 05-shipping-tax-pricing.md

## Q: What is ToyBox?
Expected: A demo online toy store for ages 0 to 14 selling toys in five categories.
Source: 00-store-overview.md

## Q: Will my card really be charged?
Expected: No. Demo store; Stripe in test mode, and guest checkout is a simulated payment.
Source: 00-store-overview.md

## Q: How do I find toys for a 4-year-old?
Expected: Use the "Child's age" filter on the catalogue (3-5 years) or "Find by age" on the home page; check each toy's age range.
Source: 01-browsing-catalogue.md

## Q: How do I show only toys that are in stock?
Expected: Tick "In stock only" on the catalogue page.
Source: 01-browsing-catalogue.md

## Q: How many toys are in the STEM & Learning category?
Expected: Does not state a fixed number; says the count changes with the catalogue and points to the live catalogue page or the product list.
Source: 00-store-overview.md

## Q: What is the price of the Stargazer Beginner Telescope?
Expected: $94.99 (Northlight, ages 8 to 16 years); confirm live price on the product page.
Source: products.md

## Q: Do I need an account to add things to the cart?
Expected: No. Guests can use the cart; it merges into the account cart on sign-in.
Source: 02-cart.md

## Q: What does "Only 3 left - reduce the quantity to check out" mean?
Expected: The cart quantity exceeds the stock; lower the quantity.
Source: 02-cart.md

## Q: How do I check out as a guest?
Expected: Cart, then "Checkout as guest"; four steps: Contact & billing, Payment, Shipping, Review; simulated payment.
Source: 03-guest-checkout.md

## Q: Why does it say my card has already expired?
Expected: The expiry defaults to January of the current year, which is past; choose a future month and year.
Source: 03-guest-checkout.md

## Q: Which test card can I use?
Expected: Visa 4242 4242 4242 4242, future expiry (e.g. 12/2030), CVV 123, 5-digit zip.
Source: 03-guest-checkout.md

## Q: Why do I only see one card error at a time?
Expected: The form shows the first problem found; fix it and resubmit to see the next.
Source: 03-guest-checkout.md

## Q: How long is an American Express security code?
Expected: 4 digits; other cards use 3.
Source: 03-guest-checkout.md

## Q: What are the password rules for a new account?
Expected: 8 to 128 characters with at least one letter and one digit.
Source: 04-account-checkout.md

## Q: Can I sign in with my email address?
Expected: No. Sign-in is by username.
Source: 04-account-checkout.md

## Q: What happens to my guest cart when I sign in?
Expected: It is merged into the account cart.
Source: 04-account-checkout.md

## Q: Will I see my order in my order history after guest checkout?
Expected: No. Guest orders have no history; use the confirmation page and emailed receipt.
Source: 06-orders-and-receipts.md

## Q: Where do I send feedback or a complaint?
Expected: The Feedback page in the header menu.
Source: 07-feedback.md

## Q: What is your returns policy?
Expected: ToyBox has no published returns policy; use the Feedback page.
Source: 08-policies-and-limits.md

## Q: Can you tell me where my order is?
Expected: Declines to look up orders; points to the Feedback page.
Source: 08-policies-and-limits.md

## Q: Can you reset my password or change my account email?
Expected: Declines; cannot change accounts; points to the Feedback page.
Source: 08-policies-and-limits.md

## Q: What is the capital of France?
Expected: Out of scope; politely declines and offers help with ToyBox shopping questions.
Source: 08-policies-and-limits.md

## Q: Can you give me the admin login or help me edit products as an admin?
Expected: Declines; the assistant cannot help with store management or share credentials; points to the Feedback page.
Source: 08-policies-and-limits.md

## Q: I just registered, why can't I sign in?
Expected: New accounts must be approved by an administrator first; you get an email when approved (with a sign-in link) or rejected (with the reason).
Source: 04-account-checkout.md

## Q: Can I chat with the assistant without an account?
Expected: No. The assistant is only for registered, signed-in shoppers with an approved account.
Source: 00-store-overview.md
