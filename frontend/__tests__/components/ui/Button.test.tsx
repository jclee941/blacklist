import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Button from '@/components/ui/Button';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Plus: (props: Record<string, unknown>) => <svg data-testid="icon-plus" {...props} />,
  Trash: (props: Record<string, unknown>) => <svg data-testid="icon-trash" {...props} />,
}));

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('has type="button" by default', () => {
    render(<Button>Test</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  describe('variants', () => {
    it('applies primary variant classes by default', () => {
      render(<Button>Primary</Button>);
      const btn = screen.getByRole('button');
      expect(btn.className).toContain('bg-blue-500');
      expect(btn.className).toContain('text-white');
    });

    it('applies secondary variant classes', () => {
      render(<Button variant="secondary">Secondary</Button>);
      const btn = screen.getByRole('button');
      expect(btn.className).toContain('bg-gray-100');
      expect(btn.className).toContain('text-gray-700');
    });

    it('applies danger variant classes', () => {
      render(<Button variant="danger">Danger</Button>);
      const btn = screen.getByRole('button');
      expect(btn.className).toContain('bg-red-500');
      expect(btn.className).toContain('text-white');
    });

    it('applies ghost variant classes', () => {
      render(<Button variant="ghost">Ghost</Button>);
      const btn = screen.getByRole('button');
      expect(btn.className).toContain('bg-transparent');
      expect(btn.className).toContain('text-gray-700');
    });
  });

  describe('sizes', () => {
    it('applies md size by default', () => {
      render(<Button>Medium</Button>);
      const btn = screen.getByRole('button');
      expect(btn.className).toContain('px-4');
      expect(btn.className).toContain('py-2');
    });

    it('applies sm size', () => {
      render(<Button size="sm">Small</Button>);
      const btn = screen.getByRole('button');
      expect(btn.className).toContain('px-3');
      expect(btn.className).toContain('py-1.5');
    });

    it('applies lg size', () => {
      render(<Button size="lg">Large</Button>);
      const btn = screen.getByRole('button');
      expect(btn.className).toContain('px-6');
      expect(btn.className).toContain('py-3');
    });
  });

  describe('loading state', () => {
    it('shows spinner when loading', () => {
      render(<Button loading>Loading</Button>);
      expect(screen.getByTitle('Loading')).toBeInTheDocument();
    });

    it('disables button when loading', () => {
      render(<Button loading>Loading</Button>);
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('applies disabled styles when loading', () => {
      render(<Button loading>Loading</Button>);
      const btn = screen.getByRole('button');
      expect(btn).toBeDisabled();
      expect(btn.className).toContain('cursor-not-allowed');
    });
  });

  describe('disabled state', () => {
    it('is disabled when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>);
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('does not fire onClick when disabled', () => {
      const onClick = vi.fn();
      render(
        <Button disabled onClick={onClick}>
          Disabled
        </Button>
      );
      fireEvent.click(screen.getByRole('button'));
      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe('click handler', () => {
    it('fires onClick when clicked', () => {
      const onClick = vi.fn();
      render(<Button onClick={onClick}>Click</Button>);
      fireEvent.click(screen.getByRole('button'));
      expect(onClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('custom className', () => {
    it('appends custom className', () => {
      render(<Button className="my-custom-class">Custom</Button>);
      expect(screen.getByRole('button').className).toContain('my-custom-class');
    });
  });
});
