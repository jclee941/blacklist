'use client';

import { Activity, Menu, X } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { useState } from 'react';

export default function NavBar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const menuItems = [
    { href: '/', label: '대시보드' },
    { href: '/ip-management', label: 'IP 관리' },
    { href: '/fortinet', label: 'FortiGate' },
    { href: '/collection', label: '데이터 수집' },
    { href: '/database', label: '데이터베이스' },
    { href: '/analytics', label: '분석' },
    { href: '/settings', label: '설정' },
  ];

  return (
    <nav className="bg-gray-900 text-white shadow-lg" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center flex-shrink-0" data-testid="navbar-logo">
            <Image src="/nextrade_logo.svg" alt="Nextrade" width={120} height={40} priority />
          </Link>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center space-x-4" data-testid="navbar-desktop-menu">
            {menuItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-800 hover:text-blue-400 transition"
              >
                {item.label}
              </Link>
            ))}

            {/* System Status */}
            <div
              className="flex items-center space-x-2 ml-4 px-3 py-2 bg-gray-800 rounded-md"
              data-testid="navbar-status"
            >
              <Activity className="h-4 w-4 text-green-500" aria-hidden="true" />
              <span className="text-xs">정상</span>
            </div>
          </div>

          {/* Mobile Menu Button */}
          <button
            type="button"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 rounded-md hover:bg-gray-800 transition"
            aria-label={isMenuOpen ? '메뉴 닫기' : '메뉴 열기'}
            aria-expanded={isMenuOpen}
            aria-controls="navbar-mobile-menu"
            data-testid="navbar-menu-toggle"
          >
            {isMenuOpen ? (
              <X className="h-6 w-6" aria-hidden="true" />
            ) : (
              <Menu className="h-6 w-6" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {isMenuOpen && (
        <div
          id="navbar-mobile-menu"
          className="md:hidden bg-gray-800 border-t border-gray-700"
          data-testid="navbar-mobile-menu"
        >
          <div className="px-2 pt-2 pb-3 space-y-1">
            {menuItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block px-3 py-2 rounded-md text-base font-medium hover:bg-gray-700 hover:text-blue-400 transition"
                onClick={() => setIsMenuOpen(false)}
              >
                {item.label}
              </Link>
            ))}

            {/* Mobile System Status */}
            <div className="flex items-center space-x-2 px-3 py-2 mt-2 border-t border-gray-700">
              <Activity className="h-4 w-4 text-green-500" aria-hidden="true" />
              <span className="text-sm">시스템 정상</span>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
