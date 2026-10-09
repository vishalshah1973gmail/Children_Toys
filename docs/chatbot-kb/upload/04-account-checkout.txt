# Account Sign-up, Sign-in and Account Checkout

Topic: Creating an account, signing in, the signed-in Stripe checkout, and the success and cancel pages.
Source: /register, /login, /account, /checkout, /checkout/success, /checkout/cancel

## How do I create an account?

Choose "Create account" in the header. The page "Create your account" asks for a Username (at least 3 characters), Email, Full name (optional) and Password. Press "Create account". You are not signed in yet: the account is placed in a waiting state and the site shows a "registration approval in progress" message. A ToyBox administrator reviews every new account. You get an email when it is approved (with a link to sign in) or rejected (with the reason). You cannot sign in until the account is approved.

## What are the username and password rules?

A username is 3 to 50 characters using letters, digits, underscore, dot or hyphen. A password is 8 to 128 characters and must include at least one letter and one digit.

## I just registered, why can't I sign in?

New accounts must be approved by a ToyBox administrator first. Until then, signing in is refused with a message that your registration is awaiting approval. You will get an email when the account is approved, with a link to sign in. If it is rejected, the email gives the reason, and the sign-in page shows that the registration was rejected. A rejected shopper can register again using the same username and email, which sends the registration back for review.

## How do I sign in?

Choose "Sign in" in the header. Enter your username and password. Sign-in is by username, not by email address. If you do not have an account, use the "No account yet? Create one" link. After signing in you return to where you were headed (for example checkout), otherwise to the home page.

## What happens to my cart when I sign in?

The items in your guest cart are merged into your account cart the first time you sign in after your account is approved, so nothing is lost. When you sign out, the site switches back to the guest cart.

## How long does my sign-in last?

A sign-in lasts 30 minutes and renews quietly in the background for up to 7 days. Signing out ends the session. Pages that need an account (Checkout, Orders, Account) send you to the sign-in page if you are signed out.

## How do I change my password?

Open Account from the username menu, find "Change password", enter your Current password and a New password that meets the same rule (8 or more characters with a letter and a digit), then press "Update password".

## What does the Account page show?

The page "Your account" shows your Username, Email, Name, Role and Member since date. These details are read-only; only the password can be changed there.

## How do I check out when I am signed in?

On the Cart page press "Proceed to checkout". The checkout has three steps: 1 Contact (Email for the receipt), 2 Shipping (Full name, Address, Apartment/suite which is optional, City, State, ZIP / postal code, Country) and 3 Review & pay. The review shows the shipping address, the receipt email, the items and a "Pay" button with the total.

## Is account checkout a real payment?

Account checkout is paid through Stripe in test mode, so no real money is charged. The review step says: "Payment is taken by Stripe in test mode. Card 4242 4242 4242 4242, any future expiry and any CVC." When Stripe is not connected, the demo uses a simulated confirmation instead. Either way, an order is only marked paid after payment is confirmed, and the stock is reduced exactly once.

## What does the "Payment confirmed" page mean?

After paying, the page shows "Confirming your payment..." while it checks the order. When confirmed it shows "Payment confirmed" with the order number, total and items, plus "View order" and "Keep shopping" buttons. If the payment is not confirmed yet it shows "Order placed" and explains the order history will show it as paid once Stripe confirms.

## What does "Payment cancelled" mean?

If you leave the Stripe payment page, ToyBox shows "Payment cancelled": nothing has been charged and your cart is untouched. If an order number is shown, that order stays pending until it is paid. Use "Back to cart" or "Keep shopping" to continue.

## Should I use guest checkout or an account?

Guest checkout is quicker and needs no sign-up, but gives no order history. An account saves your orders so they appear in My orders. Both are demo payments and no real money is charged.
