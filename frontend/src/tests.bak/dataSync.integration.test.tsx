import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { DataSyncProvider, useDataSync } from '../contexts/DataSyncContext';
import { useDataSync as useDataSyncHook } from '../hooks/useDataSync';
import { useOfflineMode } from '../hooks/useOfflineMode';
import { dataSyncService } from '../services/dataSyncService';
import { offlineService } from '../services/offlineService';

// Mock services
jest.mock('../services/dataSyncService');
jest.mock('../services/offlineService');
jest.mock('../services/api');

const mockedDataSyncService = dataSyncService as jest.Mocked<typeof dataSyncService>;
const mockedOfflineService = offlineService as jest.Mocked<typeof offlineService>;

// Test component that uses data sync
function TestComponent() {
  const { setData, getData, invalidateData, isDataStale } = useDataSync();
  const { sync, isSyncing, isOnline } = useDataSyncHook();
  const { queueAction, pendingActions } = useOfflineMode();

  React.useEffect(() => {
    // Set some test data
    setData('test-key', { value: 'test-data' });
  }, [setData]);

  const handleSync = () => {
    sync();
  };

  const handleQueueAction = () => {
    queueAction('test_action', { data: 'test' });
  };

  const testData = getData('test-key');

  return (
    <div>
      <div data-testid="test-data">{testData ? JSON.stringify(testData) : 'No data'}</div>
      <div data-testid="is-syncing">{isSyncing ? 'Syncing' : 'Not syncing'}</div>
      <div data-testid="is-online">{isOnline ? 'Online' : 'Offline'}</div>
      <div data-testid="pending-actions">{pendingActions}</div>
      <div data-testid="is-stale">{isDataStale('test-key') ? 'Stale' : 'Fresh'}</div>
      <button onClick={handleSync} data-testid="sync-button">Sync</button>
      <button onClick={handleQueueAction} data-testid="queue-button">Queue Action</button>
      <button onClick={() => invalidateData('test-key')} data-testid="invalidate-button">
        Invalidate
      </button>
    </div>
  );
}

describe('Data Synchronization Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock offline service
    mockedOfflineService.getOnlineStatus.mockReturnValue(true);
    mockedOfflineService.addOnlineStatusListener.mockReturnValue(() => {});
    mockedOfflineService.getActionQueue.mockReturnValue([]);
    mockedOfflineService.getStorageUsage.mockReturnValue({
      used: 1000,
      available: 49000000,
      percentage: 0.002
    });
    mockedOfflineService.queueAction.mockReturnValue('action-123');

    // Mock data sync service
    mockedDataSyncService.syncWithServer.mockResolvedValue({
      success: true,
      conflicts: [],
      synced: ['test-key'],
      errors: []
    });
    mockedDataSyncService.shouldSync.mockReturnValue(true);
    mockedDataSyncService.isSyncInProgress.mockReturnValue(false);
  });

  it('should provide data sync context to components', async () => {
    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('test-data')).toHaveTextContent('{"value":"test-data"}');
    });

    expect(screen.getByTestId('is-online')).toHaveTextContent('Online');
    expect(screen.getByTestId('pending-actions')).toHaveTextContent('0');
  });

  it('should handle data invalidation', async () => {
    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('test-data')).toHaveTextContent('{"value":"test-data"}');
    });

    act(() => {
      screen.getByTestId('invalidate-button').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('test-data')).toHaveTextContent('No data');
    });
  });

  it('should handle sync operations', async () => {
    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    act(() => {
      screen.getByTestId('sync-button').click();
    });

    await waitFor(() => {
      expect(mockedDataSyncService.syncWithServer).toHaveBeenCalled();
    });
  });

  it('should handle offline mode', async () => {
    // Mock offline status
    mockedOfflineService.getOnlineStatus.mockReturnValue(false);

    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    expect(screen.getByTestId('is-online')).toHaveTextContent('Offline');

    act(() => {
      screen.getByTestId('queue-button').click();
    });

    await waitFor(() => {
      expect(mockedOfflineService.queueAction).toHaveBeenCalledWith('test_action', { data: 'test' });
    });
  });

  it('should handle sync conflicts', async () => {
    mockedDataSyncService.syncWithServer.mockResolvedValue({
      success: false,
      conflicts: [{
        key: 'test-key',
        localData: { value: 'local' },
        serverData: { value: 'server' },
        localVersion: 1,
        serverVersion: 2
      }],
      synced: [],
      errors: []
    });

    const onSyncError = jest.fn();

    function TestComponentWithError() {
      const { sync } = useDataSyncHook({ onSyncError });

      return (
        <button onClick={sync} data-testid="sync-button">Sync</button>
      );
    }

    render(
      <DataSyncProvider>
        <TestComponentWithError />
      </DataSyncProvider>
    );

    act(() => {
      screen.getByTestId('sync-button').click();
    });

    await waitFor(() => {
      expect(onSyncError).toHaveBeenCalled();
    });
  });

  it('should handle network status changes', async () => {
    let statusListener: (isOnline: boolean) => void = () => {};
    
    mockedOfflineService.addOnlineStatusListener.mockImplementation((listener) => {
      statusListener = listener;
      return () => {};
    });

    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    expect(screen.getByTestId('is-online')).toHaveTextContent('Online');

    // Simulate going offline
    act(() => {
      statusListener(false);
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-online')).toHaveTextContent('Offline');
    });

    // Simulate coming back online
    act(() => {
      statusListener(true);
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-online')).toHaveTextContent('Online');
    });
  });

  it('should handle data staleness', async () => {
    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    // Initially data should be fresh
    await waitFor(() => {
      expect(screen.getByTestId('is-stale')).toHaveTextContent('Fresh');
    });

    // Mock data as stale
    const { isDataStale } = useDataSync();
    jest.spyOn(React, 'useContext').mockReturnValue({
      ...useDataSync(),
      isDataStale: jest.fn().mockReturnValue(true)
    });

    // Re-render to get updated staleness
    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('is-stale')).toHaveTextContent('Stale');
    });
  });

  it('should handle sync errors gracefully', async () => {
    mockedDataSyncService.syncWithServer.mockRejectedValue(new Error('Network error'));

    const onSyncError = jest.fn();

    function TestComponentWithErrorHandler() {
      const { sync } = useDataSyncHook({ onSyncError });

      return (
        <button onClick={sync} data-testid="sync-button">Sync</button>
      );
    }

    render(
      <DataSyncProvider>
        <TestComponentWithErrorHandler />
      </DataSyncProvider>
    );

    act(() => {
      screen.getByTestId('sync-button').click();
    });

    await waitFor(() => {
      expect(onSyncError).toHaveBeenCalledWith(expect.any(Error));
    });
  });

  it('should auto-sync when coming online with queued actions', async () => {
    let statusListener: (isOnline: boolean) => void = () => {};
    
    mockedOfflineService.addOnlineStatusListener.mockImplementation((listener) => {
      statusListener = listener;
      return () => {};
    });

    mockedOfflineService.getActionQueue.mockReturnValue([
      { key: 'test', data: {}, timestamp: Date.now() }
    ]);

    render(
      <DataSyncProvider>
        <TestComponent />
      </DataSyncProvider>
    );

    // Simulate coming online with queued actions
    act(() => {
      statusListener(true);
    });

    await waitFor(() => {
      expect(mockedDataSyncService.syncWithServer).toHaveBeenCalled();
    });
  });
});