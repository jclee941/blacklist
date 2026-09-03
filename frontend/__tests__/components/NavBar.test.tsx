import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createElement } from 'react';
import NavBar from '../../components/NavBar';

const { mockLogout, mockReplace } = vi.hoisted(() => ({
  mockLogout: vi.fn(),
  mockReplace: vi.fn(),
}));

// Mock Next.js modules
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock('next/image', () => ({
  default: ({
    src,
    alt,
    priority,
    ...props
  }: {
    src: string;
    alt: string;
    priority?: boolean;
  } & React.ImgHTMLAttributes<HTMLImageElement>) =>
    createElement('img', {
      src,
      alt,
      'data-priority': priority ? 'true' : undefined,
      ...props,
    }),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

vi.mock('@/lib/api', () => ({
  logout: mockLogout,
}));

describe('NavBar Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLogout.mockResolvedValue(undefined);
  });

  it('ends the session and returns to login from the desktop navigation', async () => {
    render(<NavBar />);

    fireEvent.click(screen.getByRole('button', { name: '로그아웃' }));

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledOnce();
      expect(mockReplace).toHaveBeenCalledWith('/login');
    });
  });

  it('ends the session and returns to login from the mobile navigation', async () => {
    render(<NavBar />);

    fireEvent.click(screen.getByRole('button', { name: '메뉴 열기' }));
    const logoutButtons = screen.getAllByRole('button', { name: '로그아웃' });
    fireEvent.click(logoutButtons[logoutButtons.length - 1]);

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledOnce();
      expect(mockReplace).toHaveBeenCalledWith('/login');
    });
  });

  it('renders logo correctly', () => {
    render(<NavBar />);
    const logo = screen.getByAltText('Nextrade');
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveAttribute('src', '/nextrade_logo.svg');
  });

  it('renders all menu items', () => {
    render(<NavBar />);

    expect(screen.getByText('대시보드')).toBeInTheDocument();
    expect(screen.getByText('IP 관리')).toBeInTheDocument();
    expect(screen.getByText('FortiGate')).toBeInTheDocument();
    expect(screen.getByText('Cloudflare 연동')).toBeInTheDocument();
    // 모니터링 메뉴는 대시보드로 통합되어 제거됨
    expect(screen.getByText('데이터 수집')).toBeInTheDocument();
    expect(screen.getByText('데이터베이스')).toBeInTheDocument();
  });

  it('displays system status indicator', () => {
    render(<NavBar />);
    expect(screen.getByText('정상')).toBeInTheDocument();
  });

  it('toggles mobile menu when menu button is clicked', () => {
    render(<NavBar />);

    const menuButton = screen.getByLabelText('메뉴 열기');

    // Initially closed
    expect(screen.queryByText('시스템 정상')).not.toBeInTheDocument();

    // Open menu
    fireEvent.click(menuButton);
    expect(screen.getByText('시스템 정상')).toBeInTheDocument();

    // Close menu
    fireEvent.click(menuButton);
    expect(screen.queryByText('시스템 정상')).not.toBeInTheDocument();
  });

  it('mobile menu toggles correctly', () => {
    render(<NavBar />);

    const menuButton = screen.getByLabelText('메뉴 열기');

    // Get all IP Management links
    let ipManagementItems = screen.getAllByText('IP 관리');
    const initialCount = ipManagementItems.length;

    // Open menu - should add mobile menu items
    fireEvent.click(menuButton);
    ipManagementItems = screen.getAllByText('IP 관리');
    expect(ipManagementItems.length).toBeGreaterThan(initialCount);

    // Close menu by clicking button again
    fireEvent.click(menuButton);
    ipManagementItems = screen.getAllByText('IP 관리');
    expect(ipManagementItems.length).toBe(initialCount);
  });

  it('has correct navigation links', () => {
    render(<NavBar />);

    const dashboardLink = screen.getAllByText('대시보드')[0].closest('a');
    expect(dashboardLink).toHaveAttribute('href', '/');

    const ipManagementLinks = screen.getAllByText('IP 관리');
    expect(ipManagementLinks[0].closest('a')).toHaveAttribute('href', '/ip-management');

    const cloudflareLinks = screen.getAllByText('Cloudflare 연동');
    expect(cloudflareLinks[0].closest('a')).toHaveAttribute('href', '/cloudflare');
  });
});
