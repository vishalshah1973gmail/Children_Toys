# Guest Checkout

Topic: How to buy without an account, the four steps, card rules and common card errors.
Source: /checkout/guest

## How do I check out as a guest?

Add toys to the cart, open the Cart page and press "Checkout as guest". The guest checkout page has four steps: Contact & billing, Payment, Shipping and Review. A Summary panel on the right shows Subtotal, Shipping, Tax and Total. No account is needed. If the cart is empty, the page says "Nothing to check out" with a "Browse toys" button.

## Is guest checkout a real payment?

No. ToyBox is a demo store and guest checkout is a simulated payment. The Review step says "This is a simulated payment for demo purposes - no real card processor is contacted." The card details are checked for valid format only, and nothing is charged. Guest checkout never uses Stripe.

## What information do I enter in the guest Contact & billing step?

Step 1 asks for: Email for the receipt, Full name, Street line 1, Street line 2 (optional), City, State and Zip. Everything except Street line 2 is required, and the "Continue to payment" button stays disabled until all required fields are filled in.

## What do I enter in the guest Payment step?

Step 2 asks for: Card type (Visa, Mastercard, Discover or American Express), Card number, Name on card, expiry month (MM), expiry year (YYYY), security code (CVV) and the card's Zip. Press "Continue to shipping" to move on.

## Which card number can I use to test guest checkout?

Use the standard test Visa 4242 4242 4242 4242 with Card type set to Visa, a future expiry such as 12/2030, CVV 123 and a 5-digit zip such as 07102. That combination passes all of the card rules.

## Why does it say "This card has already expired"?

The expiry fields start filled with January of the current year, which has already passed. Change the month and year to a date in the future (for example 12/2030) and press "Continue to shipping" again. This is the most common reason a first attempt fails.

## Why does the page show only one card error at a time?

The form displays the first problem it finds and hides the others, so a shopper with several mistakes sees them one at a time. Fix the error shown, press "Continue to shipping" again, and a further error may appear. Checks happen in this order: card number (shown under the card number box), then month, expiry year, security code and zip.

## What are the card rules and error messages in guest checkout?

- Card number must be 12 to 19 digits: "Card number length looks wrong."
- It must pass the standard checksum: "Card number failed the checksum check."
- It must match the chosen card type: "That number doesn't look like a visa card." (the card type name appears in lowercase).
- Month must be 1 to 12: "Expiry month must be between 1 and 12."
- Expiry must not be in the past: "This card has already expired."
- Security code must be 3 digits, or 4 digits for American Express: "Visa security codes are 3 digits." or "Amex security codes are 4 digits."
- Card zip must be 5 digits, optionally followed by a dash and 4 more digits: "Zip code must be 5 digits (optionally +4)."

## How do I tell which card number matches which card type?

Visa starts with 4 and has 13, 16 or 19 digits. Mastercard starts with 51 to 55 or 2221 to 2720 and has 16 digits. Discover starts with 6011, 65 or 644 to 649 and has 16 digits. American Express starts with 34 or 37 and has 15 digits.

## What do I enter in the guest Shipping step?

Step 3 has a "Same as billing address" checkbox, ticked by default. Untick it to enter a different shipping address: Full name, Street line 1, City, State and Zip, all required. Then press "Review order".

## What happens when I press Pay on the guest Review step?

Step 4 lists each item with its quantity and line total and a button such as "Pay $101.29" showing the order total. After paying, the page says "Order placed" with the order number and total, lists the items and the "Shipping to" address, and offers a "Keep shopping" button. The cart is emptied. The order is recorded as paid straight away, and the stock for each toy goes down immediately.

## Will I get a receipt email after guest checkout?

The store tries to email a receipt to the address you entered. If it works, the page says "A receipt was emailed to" your address. If the email cannot be sent, the page says "We couldn't email your receipt, but your order is confirmed below." The order is confirmed either way, so keep the confirmation page details. Pictures in the email only show when the store's public web address is reachable from the internet.

## Can I see my guest order later?

No. Guests have no order history. The confirmation page and the emailed receipt are the only record. Create an account before checking out if you want orders saved in an order history.
