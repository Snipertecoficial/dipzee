import { clearAccessToken, getAccessToken, setAccessToken } from './session';

afterEach(() => clearAccessToken());

test('keeps the access token in process memory only', () => {
  const storageSpy = vi.spyOn(Storage.prototype, 'setItem');
  setAccessToken('short-lived-token');
  expect(getAccessToken()).toBe('short-lived-token');
  expect(storageSpy).not.toHaveBeenCalled();
  storageSpy.mockRestore();
});

test('clears the access token', () => {
  setAccessToken('token');
  clearAccessToken();
  expect(getAccessToken()).toBeNull();
});
