import { Outlet } from 'react-router-dom'

import ChatWidget from './ChatWidget'
import Footer from './Footer'
import Navbar from './Navbar'

/** Shell shared by every storefront route. */
export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex w-full flex-1 flex-col px-4 py-8 sm:px-8 xl:px-12">
        <Outlet />
      </main>
      <Footer />
      <ChatWidget />
    </div>
  )
}
