import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Input from '@/components/ui/Input';

describe('Input', () => {
  it('renders an input element', () => {
    render(<Input />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders with placeholder', () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  describe('label', () => {
    it('renders label when provided', () => {
      render(<Input label="Username" />);
      expect(screen.getByText('Username')).toBeInTheDocument();
    });

    it('associates label with input via htmlFor', () => {
      render(<Input label="Email" id="email-input" />);
      const label = screen.getByText('Email');
      expect(label).toHaveAttribute('for', 'email-input');
    });

    it('shows required asterisk', () => {
      render(<Input label="Name" required />);
      expect(screen.getByText('*')).toBeInTheDocument();
    });

    it('does not show asterisk when not required', () => {
      render(<Input label="Name" />);
      expect(screen.queryByText('*')).not.toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message', () => {
      render(<Input error="This field is required" />);
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    it('sets aria-invalid to true when error', () => {
      render(<Input error="Error" />);
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
    });

    it('sets aria-invalid to false when no error', () => {
      render(<Input />);
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'false');
    });

    it('applies red border classes on error', () => {
      render(<Input error="Error" />);
      const input = screen.getByRole('textbox');
      expect(input.className).toContain('border-red-300');
    });

    it('applies normal border when no error', () => {
      render(<Input />);
      const input = screen.getByRole('textbox');
      expect(input.className).toContain('border-gray-300');
    });
  });

  describe('hint', () => {
    it('shows hint text', () => {
      render(<Input hint="Enter your email address" />);
      expect(screen.getByText('Enter your email address')).toBeInTheDocument();
    });

    it('hides hint when error is present', () => {
      render(<Input hint="A helpful hint" error="Error message" />);
      expect(screen.queryByText('A helpful hint')).not.toBeInTheDocument();
      expect(screen.getByText('Error message')).toBeInTheDocument();
    });
  });

  describe('disabled state', () => {
    it('disables input', () => {
      render(<Input disabled />);
      expect(screen.getByRole('textbox')).toBeDisabled();
    });
  });

  describe('value and onChange', () => {
    it('fires onChange', () => {
      const onChange = vi.fn();
      render(<Input onChange={onChange} />);
      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'test' } });
      expect(onChange).toHaveBeenCalled();
    });
  });

  describe('custom className', () => {
    it('appends custom className', () => {
      render(<Input className="custom" />);
      expect(screen.getByRole('textbox').className).toContain('custom');
    });
  });

  describe('aria-describedby', () => {
    it('links to error element', () => {
      render(<Input id="test" error="Error" />);
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-describedby', 'test-error');
    });

    it('links to hint element when no error', () => {
      render(<Input id="test" hint="Hint" />);
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-describedby', 'test-hint');
    });
  });
});
