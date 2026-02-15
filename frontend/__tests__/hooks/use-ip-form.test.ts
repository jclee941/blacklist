import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useIPForm } from '@/app/ip-management/hooks/use-ip-form';

describe('useIPForm', () => {
  it('initializes with default values', () => {
    const { result } = renderHook(() => useIPForm());

    expect(result.current.formData.ip_address).toBe('');
    expect(result.current.formData.reason).toBe('');
    expect(result.current.formData.source).toBe('MANUAL');
    expect(result.current.formData.country).toBe('');
    expect(result.current.formData.is_active).toBe(true);
    expect(result.current.formData.detection_date).toBe('');
    expect(result.current.formData.removal_date).toBe('');
  });

  it('has no submit error on init', () => {
    const { result } = renderHook(() => useIPForm());

    expect(result.current.submitError).toBeNull();
  });

  // --- resetForm ---

  it('resets form to defaults', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.updateField('ip_address', '10.0.0.1');
      result.current.updateField('reason', 'test');
    });

    act(() => {
      result.current.resetForm();
    });

    expect(result.current.formData.ip_address).toBe('');
    expect(result.current.formData.reason).toBe('');
  });

  it('resets clears submit error', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.setSubmitError('some error');
    });

    act(() => {
      result.current.resetForm();
    });

    expect(result.current.submitError).toBeNull();
  });

  // --- updateField ---

  it('updates a single field', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.updateField('reason', 'Malicious activity');
    });

    expect(result.current.formData.reason).toBe('Malicious activity');
  });

  it('updates source field', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.updateField('source', 'REGTECH');
    });

    expect(result.current.formData.source).toBe('REGTECH');
  });

  // --- handleIPChange (formatIPAddress) ---

  it('formats IP address with dots', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.handleIPChange('192168001001');
    });

    // formatIPAddress uses regex to insert dots between digit groups
    expect(result.current.formData.ip_address).toContain('.');
  });

  it('handles valid IP address', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.handleIPChange('10.0.0.1');
    });

    expect(result.current.formData.ip_address).toBe('10.0.0.1');
  });

  it('handles empty IP input', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.handleIPChange('');
    });

    expect(result.current.formData.ip_address).toBe('');
  });

  // --- handleDetectionDateChange ---

  it('sets detection date', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.handleDetectionDateChange('2025-01-15');
    });

    expect(result.current.formData.detection_date).toBe('2025-01-15');
  });

  it('auto-calculates removal date +3 months for non-REGTECH', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.updateField('source', 'MANUAL');
    });

    act(() => {
      result.current.handleDetectionDateChange('2025-01-15');
    });

    // Should auto-set removal_date to approximately 3 months later
    expect(result.current.formData.removal_date).not.toBe('');
    expect(result.current.formData.removal_date).toMatch(/^\d{4}-\d{2}-\d{2}/);
  });

  it('REGTECH with existing removal date keeps it', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.updateField('source', 'REGTECH');
      result.current.updateField('removal_date', '2025-06-01');
    });

    act(() => {
      result.current.handleDetectionDateChange('2025-01-15');
    });

    // REGTECH keeps existing removal_date
    expect(result.current.formData.removal_date).toBe('2025-06-01');
  });

  it('empty detection date only clears detection_date', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.handleDetectionDateChange('2025-01-15');
    });

    act(() => {
      result.current.handleDetectionDateChange('');
    });

    expect(result.current.formData.detection_date).toBe('');
  });

  // --- populateFromRecord ---

  it('populates form from record', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.populateFromRecord({
        id: 1,
        ip_address: '10.0.0.1',
        reason: 'Malware',
        source: 'REGTECH',
        country: 'KR',
        is_active: true,
        detection_date: '2025-01-15',
        removal_date: '2025-04-15',
        created_at: '2025-01-15',
        updated_at: '2025-01-15',
      });
    });

    expect(result.current.formData.ip_address).toBe('10.0.0.1');
    expect(result.current.formData.reason).toBe('Malware');
    expect(result.current.formData.source).toBe('REGTECH');
    expect(result.current.formData.country).toBe('KR');
  });

  it('populate clears submit error', () => {
    const { result } = renderHook(() => useIPForm());

    act(() => {
      result.current.setSubmitError('old error');
    });

    act(() => {
      result.current.populateFromRecord({
        id: 1,
        ip_address: '10.0.0.1',
        reason: 'Test',
        source: 'MANUAL',
        country: '',
        created_at: '2025-01-15',
        updated_at: '2025-01-15',
      });
    });

    expect(result.current.submitError).toBeNull();
  });
});
